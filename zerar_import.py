
from app import create_app, db
from app.models import ImportState

app = create_app()
with app.app_context():
    ImportState.query.filter_by(key='talents_form').delete()
    db.session.commit()
    print('ImportState deletado')
