"""Trading Engine Service.

Handles transaction execution, balance deduction/addition, portfolio 
position tracking (buying and selling fractional shares), and transaction logging.
"""

from database.models import SessionLocal, User, Portfolio, Transaction

def execute_trade(
    user_id: int, 
    ticker: str, 
    asset_type: str, 
    action: str, 
    shares: float, 
    price: float
) -> bool:
    """Execute a BUY or SELL order, updating user balance and portfolio holdings."""
    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if not user:
            return False
        
        cost = price * shares
        action = action.upper()

        if action == "BUY":
            # Verify user has enough cash balance
            if user.balance < cost:
                return False
            
            # Deduct cash
            user.balance -= cost

            # Check if user already owns this asset
            portfolio = session.query(Portfolio).filter_by(user_id=user_id, ticker=ticker).first()
            if portfolio:
                # Recalculate weighted average cost
                total_cost = (portfolio.shares * portfolio.avg_cost) + cost
                portfolio.shares += shares
                portfolio.avg_cost = total_cost / portfolio.shares
            else:
                new_holding = Portfolio(
                    user_id=user_id,
                    ticker=ticker,
                    asset_type=asset_type,
                    shares=shares,
                    avg_cost=price
                )
                session.add(new_holding)

        elif action == "SELL":
            # Check if user owns the asset and has enough shares
            portfolio = session.query(Portfolio).filter_by(user_id=user_id, ticker=ticker).first()
            if not portfolio or portfolio.shares < shares:
                return False
            
            # Credit cash back
            user.balance += cost
            portfolio.shares -= shares

            # Remove portfolio row if shares drop to zero (accounting for tiny float precision)
            if portfolio.shares <= 0.00005:
                session.delete(portfolio)
        else:
            return False

        # Record immutable transaction in the ledger
        tx = Transaction(
            user_id=user_id,
            ticker=ticker,
            action=action,
            shares=shares,
            price=price
        )
        session.add(tx)
        
        session.commit()
        return True

    except Exception as ex:
        session.rollback()
        print(f"Error executing trade for user {user_id}: {ex}")
        return False
    finally:
        session.close()