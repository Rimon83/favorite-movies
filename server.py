from flask import Flask, render_template, redirect, url_for, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired
from wtforms.widgets import TextInput
from flask_bootstrap import Bootstrap5

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
import requests
import os

url = os.environ["MOVIE_URL"]
url_image = os.environ["IMAGE_URL"].strip()
database_url = os.environ["DB_URL"]


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ["SECRET_KEY"]
bootstrap = Bootstrap5(app)

response = requests.get(url)
data = response.json()
movies_list = data["results"]



class Base(DeclarativeBase):
    pass


if not database_url:
    raise ValueError("No DATABASE_URL set for Flask application")
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
db = SQLAlchemy(model_class=Base)
# Initialise the app with the extension
db.init_app(app)


class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    rating: Mapped[float] = mapped_column(Float)
    ranking: Mapped[int] = mapped_column(Integer)
    review: Mapped[str] = mapped_column(String(25))
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


# create update movie form
class BootstrapTextInput(TextInput):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        return super().__call__(field, **kwargs)


class UpdateMovie(FlaskForm):
    rating = FloatField(label="Rating (out of 10)", widget=BootstrapTextInput(), validators=[DataRequired()])
    review = StringField(label='Review', widget=BootstrapTextInput(), validators=[DataRequired()])
    done = SubmitField(label="Done", render_kw={'class': 'btn btn-primary'})


@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    all_movies = result.scalars().all()
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()
    return render_template('index.html', movies=all_movies)


@app.route("/edit/<int:movie_id>", methods=["GET", "POST"])
def edit(movie_id):
    movie = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
    update_movie = UpdateMovie(obj=movie)
    if request.method == 'POST' and update_movie.validate_on_submit():
        movie.rating = update_movie.rating.data
        movie.review = update_movie.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit.html', form=update_movie, movie_id=movie_id)


@app.route("/delete/<int:movie_id>")
def delete(movie_id):
    movie_to_delete = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/select")
def select():
    return render_template("select.html", movies_list=movies_list, url=url_image)


@app.route("/add/<int:movie_id>")
def add(movie_id):
    movie_by_id = [movie for movie in movies_list if movie["id"] == movie_id]
    with app.app_context():
        new_movie = Movie(
            title=movie_by_id[0]["title"],
            year=movie_by_id[0]["release_date"].split("-")[0],
            description=movie_by_id[0]["overview"],
            img_url=f"{url_image}{movie_by_id[0]['poster_path']}",
            rating=0,
            ranking=0,
            review="No review yet"
        )
        db.session.add(new_movie)
        db.session.commit()

    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
