import sys
import os
import typing as t
import argparse
try:
    from UPIGUARD.src.db import SessionLocal, User, Merchant, Transaction
except ImportError:
    parent = os.path.dirname(os.path.dirname(__file__))
    if parent not in sys.path:
        sys.path.insert(0, parent)
    from src.db import SessionLocal, User, Merchant, Transaction

MODELS = {
    "users": User,
    "merchants": Merchant,
    "transactions": Transaction,
}

def _pk_field(Model):
    if hasattr(Model, "id"):
        return Model.id
    if hasattr(Model, "merchant_id"):
        return Model.merchant_id
    return None

def _convert_type(value: str, target_type: t.Any):
    try:
        if target_type is int:
            return int(value)
        if target_type is float:
            return float(value)
        return value
    except Exception:
        return value

def _format_row(entity: str, r: t.Any) -> str:
    if entity == "users":
        return f"User(id={r.id}, name={r.name}, email={r.email}, role={r.role}, upi={r.upi})"
    if entity == "merchants":
        return f"Merchant(merchant_id={r.merchant_id}, user_id={r.user_id}, category={r.category}, qr_code={r.qr_code})"
    if entity == "transactions":
        return f"Txn(id={r.id}, sender={r.sender}, receiver={r.receiver}, amount={r.amount}, prediction={r.prediction}, timestamp={r.timestamp})"
    return str(r)

def cmd_list(entity: str, limit: int, order: str):
    Model = MODELS[entity]
    s = SessionLocal()
    try:
        q = s.query(Model)
        key = _pk_field(Model)
        if key is not None:
            q = q.order_by(key.desc() if order.lower().startswith("d") else key.asc())
        rows = q.limit(limit).all()
        if not rows:
            print("No records found.")
            return
        for r in rows:
            print(_format_row(entity, r))
    finally:
        s.close()

def cmd_show(entity: str, record_id: int):
    Model = MODELS[entity]
    pk = _pk_field(Model)
    s = SessionLocal()
    try:
        row = s.query(Model).filter(pk == record_id).first()
        if not row:
            print("Not found")
            return
        print(_format_row(entity, row))
    finally:
        s.close()

def cmd_update(entity: str, record_id: int, updates: t.List[str]):
    Model = MODELS[entity]
    pk = _pk_field(Model)
    changes = {}
    for item in updates:
        if "=" not in item:
            print(f"Skipping invalid token: {item}")
            continue
        k, v = item.split("=", 1)
        changes[k.strip()] = v.strip()
    if not changes:
        print("Provide at least one KEY=VALUE update")
        return
    s = SessionLocal()
    try:
        row = s.query(Model).filter(pk == record_id).first()
        if not row:
            print("Record not found")
            return
        applied = []
        for k, v in changes.items():
            if not hasattr(row, k):
                print(f"Skip unknown field: {k}")
                continue
            cur = getattr(row, k)
            setattr(row, k, _convert_type(v, type(cur)))
            applied.append(k)
        s.add(row)
        s.commit()
        print(f"Updated {entity} id={record_id}: {', '.join(applied)}")
    except Exception as e:
        s.rollback()
        print(f"Update failed: {e}")
    finally:
        s.close()

def cmd_delete(entity: str, record_id: int):
    Model = MODELS[entity]
    pk = _pk_field(Model)
    s = SessionLocal()
    try:
        row = s.query(Model).filter(pk == record_id).first()
        if not row:
            print("Record not found")
            return
        s.delete(row)
        s.commit()
        print(f"Deleted {entity} id={record_id}")
    except Exception as e:
        s.rollback()
        print(f"Delete failed: {e}")
    finally:
        s.close()

def main():
    parser = argparse.ArgumentParser(description="Simple DB admin for viewing and editing records")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List records")
    p_list.add_argument("entity", choices=list(MODELS.keys()))
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--order", choices=["asc", "desc"], default="desc")

    p_show = sub.add_parser("show", help="Show one record")
    p_show.add_argument("entity", choices=list(MODELS.keys()))
    p_show.add_argument("record_id", type=int)

    p_update = sub.add_parser("update", help="Update fields with KEY=VALUE pairs")
    p_update.add_argument("entity", choices=list(MODELS.keys()))
    p_update.add_argument("record_id", type=int)
    p_update.add_argument("updates", nargs=argparse.REMAINDER)

    p_delete = sub.add_parser("delete", help="Delete a record")
    p_delete.add_argument("entity", choices=list(MODELS.keys()))
    p_delete.add_argument("record_id", type=int)

    args = parser.parse_args()
    if args.cmd == "list":
        cmd_list(args.entity, args.limit, args.order)
    elif args.cmd == "show":
        cmd_show(args.entity, args.record_id)
    elif args.cmd == "update":
        cmd_update(args.entity, args.record_id, args.updates)
    elif args.cmd == "delete":
        cmd_delete(args.entity, args.record_id)

if __name__ == "__main__":
    main()
