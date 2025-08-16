import os
from flask import Flask, request, jsonify
from db.connection import session
from db.models import User, Profile, UserRole

app = Flask(__name__)


def serialize_user(u: User):
    return {
        "id": u.id,
        "email": getattr(u, "email", None),
        "first_name": getattr(u, "first_name", None),
        "last_name": getattr(u, "last_name", None),
        "phone_number": getattr(u, "phone_number", None),
        "role": getattr(u, "role", None).name if hasattr(getattr(u, "role", None), 'name') else getattr(u, "role", None),
        "blocked": getattr(u, "blocked", None),
        "deleted": getattr(u, "deleted", None),
        # Expose user's default currency as 'currency' to the UI
        "currency": getattr(u, "default_currency", None) or getattr(getattr(u, "profile", None), "currency", None),
    }


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/admin/users', methods=['GET'])
def admin_list_users():
    """List users with optional filters and pagination."""
    q = session.query(User)

    # Filters
    email = request.args.get('email')
    role = request.args.get('role')
    blocked = request.args.get('blocked')
    deleted = request.args.get('deleted')
    currency = request.args.get('currency')

    if email:
        q = q.filter(User.email.ilike(f"%{email}%"))
    if role:
        try:
            # Accept enum name or raw value
            enum_role = UserRole[role] if role in UserRole.__members__ else role
            q = q.filter(User.role == enum_role)
        except Exception:
            pass
    if blocked is not None:
        if blocked.lower() in ('true', '1'):
            q = q.filter(getattr(User, 'blocked', False) == True)  # noqa: E712
        elif blocked.lower() in ('false', '0'):
            q = q.filter(getattr(User, 'blocked', False) == False)  # noqa: E712
    if deleted is not None:
        if deleted.lower() in ('true', '1'):
            q = q.filter(getattr(User, 'deleted', False) == True)  # noqa: E712
        elif deleted.lower() in ('false', '0'):
            q = q.filter(getattr(User, 'deleted', False) == False)  # noqa: E712
    if currency:
        # Prefer user.default_currency if exists else join profile.currency
        if hasattr(User, 'default_currency'):
            q = q.filter(getattr(User, 'default_currency') == currency)
        else:
            q = q.join(Profile, isouter=True).filter(Profile.currency == currency)

    # Pagination
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
    except Exception:
        page, page_size = 1, 25

    total = q.count()
    items = q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "items": [serialize_user(u) for u in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@app.route('/admin/users/<int:user_id>', methods=['GET'])
def admin_get_user(user_id: int):
    u = session.query(User).filter(User.id == user_id).first()
    if not u:
        return jsonify({"error": "User not found"}), 404
    return jsonify(serialize_user(u))


@app.route('/admin/users/<int:user_id>', methods=['PATCH'])
def admin_patch_user(user_id: int):
    payload = request.get_json(silent=True) or {}
    u = session.query(User).filter(User.id == user_id).first()
    if not u:
        return jsonify({"error": "User not found"}), 404

    # Allowed updatable fields (apply if present and attribute exists)
    updatable_direct = ["role", "blocked", "deleted", "default_currency"]
    # Map alias 'currency' -> 'default_currency' if provided
    if 'currency' in payload and 'default_currency' not in payload:
        payload['default_currency'] = payload['currency']

    for field in updatable_direct:
        if field in payload and hasattr(u, field):
            val = payload[field]
            if field == "role":
                try:
                    # Accept role as string (e.g., 'ADMIN'/'USER') or enum
                    if isinstance(val, str):
                        val = UserRole[val] if val in UserRole.__members__ else val
                except Exception:
                    pass
            setattr(u, field, val)

    # If default_currency not on User, fall back to Profile.currency
    if 'default_currency' in payload and not hasattr(u, 'default_currency'):
        prof = session.query(Profile).filter(Profile.user_id == u.id).first()
        if prof:
            prof.currency = payload['default_currency']

    session.commit()
    return jsonify(serialize_user(u))


if __name__ == '__main__':
    port = int(os.getenv('PORT', '3000'))
    app.run(host='0.0.0.0', port=port, debug=True)