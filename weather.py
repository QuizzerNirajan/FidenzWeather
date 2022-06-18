import email
from flask import Flask,render_template,  redirect, session, url_for 
from flask_caching import Cache 

from os import environ as env # for the environment variable configuration

from dotenv import find_dotenv, load_dotenv # to search and load environment file 

from urllib.parse import quote_plus, urlencode # to encode the url

from authlib.integrations.flask_client import OAuth #for Auth0
import requests, json

# load the .env configuration file
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


config = {
    "DEBUG": True,          # Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 3 # set default time to 300 seconds
}
app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

#configure Auth0 applicaiton authentication
oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

app.config.from_mapping(config) # map the config to the Flask app

cache = Cache(app) #initialize cache

# Function for caching and city weather
@cache.cached( timeout=300 ) # cache the response for 5 minutes
def get_weather():
    json_URL = "./cities.json"
    json_file = open (json_URL, 'r')
    json_list = json.load(json_file)

    cityCodes = []


    for x in json_list["List"]:

        cityCodes.append(x["CityCode"])

    # define the opeanweatherapi key
    API_KEY = '002696c65f8c7d7a510696f90bc40926'

    # generate the url
    url = "http://api.openweathermap.org/data/2.5/group?id=" + ",".join(cityCodes) + "&units=metric&appid="+ API_KEY

    # get the response from the url
    response = requests.get(url).json()
    
    # get the list of cities
    weather_data = []
    for data in response["list"]:
        a = {}
        a["id"] = data["id"]
        a["name"] = data["name"]
        a["temp"] = data["main"]["temp"]
        a["description"] = data["weather"][0]["description"]
        weather_data.append(a)
    return weather_data


# Add route for login
# Vistors visitng the login route would be
# redirected to Auth0 for the authentication process

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

# After logging in with Auth0, the user would be returned to the callback route
# Here, the session of the user is saved so that, the user wont have to
# sign in again at a later visit

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

# Responsbile for the sign out of the user. 
# First clear's user session on the server application

# then also makes sure that the Auth0 session is clear 

@app.route("/logout")
def logout():
    session.clear()
    with app.app_context():
        cache.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True), # redirect to the home page
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )



@app.route("/")
def home():
    return render_template("home.html", session=session.get('user'), indent=4)
 

@app.route('/climate', methods=['GET']) # decorator 

def climate():
    print(session.get('user'))


    if session.get('user') is not None:
        weather_data = get_weather()
        return render_template("climate.html", weather_data=weather_data)
    else:
        return redirect(url_for("home"))



if __name__ == '__main__':
    app.run(debug=True)
