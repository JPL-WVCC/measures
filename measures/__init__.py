from pkg_resources import get_distribution
from flask import Flask


__version__ = get_distribution('measures').version


app = Flask(__name__)
app.config.from_pyfile('../settings.cfg')

# views blueprints

# services blueprints
