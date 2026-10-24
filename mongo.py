from pymongo import MongoClient
uri = "mongodb+srv://siddhirajjamdar:1af2xPBGJZCW3CsS@tutedude.v830z55.mongodb.net/"
client = MongoClient(uri)
try:
    client.admin.command("ping")
    print("Connected successfully")
    client.close()

except Exception as e:
    raise Exception(
        "The following error occurred: ", e)


@app.route("/")
def home():
    day_of_week = datetime.now().strftime("%A")
    current_time = datetime.now().strftime("%H:%M:%S")

    return render_template(
        "index.html",
        current_time=current_time,
        day_of_week=day_of_week
    )

