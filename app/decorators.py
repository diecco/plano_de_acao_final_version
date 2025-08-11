from functools import wraps
from flask import redirect, session, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login para acessar esta página.')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function
