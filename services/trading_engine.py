from datetime import datetime, timezone

from database.models import SessionLocal, Transaction, User, Portfolio

ACTION_BUY = "BUY"
ACTION_SELL = "SELL"


def _new_session():
    return SessionLocal()


def execute_trade(user_id: int, ticker: str, asset_type: str, action: str, shares: float, price: float) -> bool:
    """Execute a BUY or SELL trade in the paper trading portfolio.

    Returns True if the trade succeeded, False otherwise.
    """
    session = _new_session()
    try:
        user = session.get(User, user_id)
        if user is None:
            return False

        total_cost = shares * price

        if action == ACTION_BUY:
            if user.balance < total_cost:
                return False
            user.balance -= total_cost

            portfolio = session.scalar(
                Portfolio.__table__.select()
                .where(Portfolio.user_id == user_id)
                .where(Portfolio.ticker == ticker)
            )
            if portfolio is not None:
                portfolio.shares += shares
                portfolio.avg_cost = (
                    portfolio.avg_cost * portfolio.shares - shares * price
                ) / portfolio.shares if portfolio.shares else 0.0
            else:
                session.add(
                    Portfolio(
                        user_id=user_id,
                        ticker=ticker,
                        asset_type=asset_type,
                        shares=shares,
                        avg_cost=price,
                    )
                )

        elif action == ACTION_SELL:
            portfolio = session.scalar(
                Portfolio.__table__.select()
                .where(Portfolio.user_id == user_id)
                .where(Portfolio.ticker == ticker)
            )
            if portfolio is None or portfolio.shares < shares:
                return False
            proceeds = shares * price
            user.balance += proceeds
            portfolio.shares -= shares
            if portfolio.shares <= 0:
                session.delete(portfolio)

        else:
            return False

        session.add(
            Transaction(
                user_id=user_id,
                ticker=ticker,
                action=action,
                shares=shares,
                price=price,
                timestamp=datetime.now(timezone.utc),
            )
        )

        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()
