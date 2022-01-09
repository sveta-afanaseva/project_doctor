from app import app, db
from app.models import User, Appointment


@app.shell_context_processor
def make_shell_context():
    return {"db": db, "User": User, "Appointment": Appointment}

if __name__ == "__main__":
    app.run(debug=True)