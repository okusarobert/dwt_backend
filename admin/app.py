from flask import Flask, url_for, request, redirect, render_template, flash
from markupsafe import Markup
from flask_admin import Admin, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from db.models import User, Profile, UserRole  # import your models
from db.dto import validate_login, LoginDto
from db.wallet import Account, Transaction, CryptoAddress, Reservation, Swap  # import all wallet models
from db.connection import session  # adjust as needed
from decouple import config

app = Flask(__name__)
app.secret_key = config('APP_SECRET')  # Needed for Flask-Admin and Flask-Login

# --- Flask-Login setup ---
login_manager = LoginManager(app)
login_manager.login_view = 'login_view'

# Use User model for admin authentication (must have is_admin flag)
class AdminUser(UserMixin):
    def __init__(self, user):
        self.id = user.id
        self.email = user.email
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.is_admin = getattr(user, 'is_admin', True)  # fallback for demo
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    user = session.query(User).filter_by(id=int(user_id)).first()
    if user:
        return AdminUser(user)
    return None

# --- Admin authentication views ---
@app.route('/admin/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Replace with real password check and admin check
        data = LoginDto(**request.form)
        errors = validate_login(data, session)
        if not errors:
            user = session.query(User).filter_by(email=email).first()
            if user and user.role == UserRole.ADMIN:
                login_user(AdminUser(user))
                return redirect(url_for('admin.index'))
            flash('Invalid credentials or not an admin.')
        else:
            flash("Invalid credentials or not an admin. ")
    return render_template('login.html')

@app.route('/admin/logout')
def logout_view():
    logout_user()
    return redirect(url_for('login_view'))

# --- Protect admin views ---
class AuthenticatedAdminIndexView(AdminIndexView):
    @expose('/')
    @login_required
    def index(self):
        return super().index()

class AuthenticatedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', True)
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login_view'))

admin = Admin(app, name='Admin', template_mode='bootstrap3', index_view=AuthenticatedAdminIndexView())

# Custom UserAdmin with 'Create Account' link
class UserAdmin(AuthenticatedModelView):
    column_list = ('id', 'email', 'create_account')
    column_formatters = {
        'create_account': lambda v, c, m, p: Markup(
            f'<a href="{url_for("account.create_view")}?user_id={m.id}">Create Account</a>'
        )
    }
    column_labels = {'create_account': 'Create Account'}

# Custom AccountAdmin with user_id pre-fill
class AccountAdmin(AuthenticatedModelView):
    form_choices = {
        'account_type': [
            ('FIAT', 'FIAT'),
            ('CRYPTO', 'CRYPTO')
        ]
    }
    # Only include 'user' (relationship) in form_columns
    form_columns = ['user', 'currency', 'account_type', 'account_number', 'label', 'balance', 'locked_amount']
    # Add a column for user's full name
    column_list = ('user_full_name', 'user', 'currency', 'account_type', 'account_number', 'label', 'balance', 'locked_amount')
    column_formatters = {
        'user_full_name': lambda v, c, m, p: f"{m.user.first_name} {m.user.last_name}" if m.user else ""
    }
    column_labels = {'user_full_name': 'User Full Name'}
    def create_form(self, obj=None):
        form = super().create_form(obj)
        user_id = request.args.get('user_id')
        if user_id and hasattr(form, 'user'):
            try:
                user_obj = session.query(User).get(int(user_id))
                if user_obj:
                    form.user.data = user_obj
            except Exception:
                pass
        return form

# Transaction admin to list all transactions
class TransactionAdmin(AuthenticatedModelView):
    page_size = 50
    column_list = ('user_full_name', 'account_number', 'amount', 'type', 'status', 'created_at')
    column_formatters = {
        'user_full_name': lambda v, c, m, p: f"{m.account.user.first_name} {m.account.user.last_name}" if m.account and m.account.user else "",
        'account_number': lambda v, c, m, p: m.account.account_number if m.account else ""
    }
    column_labels = {
        'user_full_name': 'User Full Name',
        'account_number': 'Account Number',
        'amount': 'Amount',
        'type': 'Type',
        'status': 'Status',
        'created_at': 'Created At'
    }

# CryptoAddress admin
class CryptoAddressAdmin(AuthenticatedModelView):
    page_size = 50
    column_list = ('account_number', 'currency_code', 'address', 'label', 'is_active', 'memo', 'address_type', 'version')
    column_formatters = {
        'account_number': lambda v, c, m, p: m.account.account_number if m.account else ""
    }
    column_labels = {
        'account_number': 'Account Number',
        'currency_code': 'Currency',
        'address': 'Address',
        'label': 'Label',
        'is_active': 'Active',
        'memo': 'Memo',
        'address_type': 'Address Type',
        'version': 'Version'
    }

# Reservation admin
class ReservationAdmin(AuthenticatedModelView):
    page_size = 50
    column_list = ('user_id', 'reference', 'amount', 'type', 'status')
    column_labels = {
        'user_id': 'User ID',
        'reference': 'Reference',
        'amount': 'Amount',
        'type': 'Type',
        'status': 'Status'
    }

# Swap admin
class SwapAdmin(AuthenticatedModelView):
    page_size = 50
    column_list = ('user_id', 'from_account_id', 'to_account_id', 'from_amount', 'to_amount', 'rate', 'fee_amount', 'status', 'transaction_id')
    column_labels = {
        'user_id': 'User ID',
        'from_account_id': 'From Account',
        'to_account_id': 'To Account',
        'from_amount': 'From Amount',
        'to_amount': 'To Amount',
        'rate': 'Rate',
        'fee_amount': 'Fee',
        'status': 'Status',
        'transaction_id': 'Transaction ID'
    }

admin.add_view(UserAdmin(User, session))
admin.add_view(AuthenticatedModelView(Profile, session))
admin.add_view(AccountAdmin(Account, session))
admin.add_view(TransactionAdmin(Transaction, session))
admin.add_view(CryptoAddressAdmin(CryptoAddress, session))
admin.add_view(ReservationAdmin(Reservation, session))
admin.add_view(SwapAdmin(Swap, session))
# Add more models as needed

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)