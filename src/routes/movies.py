from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MoviePartialUpdateSchema
)


router = APIRouter()


# Write your code here
@router.get("/movies/", response_model=MovieListResponseSchema, tags=["movies"])
async def get_movies(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20)
):
    total_items = await db.scalar(select(func.count(MovieModel.id)))
    if total_items == 0:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = (total_items + per_page - 1) // per_page
    if page > total_pages:
        raise HTTPException(status_code=404, detail="No movies found.")

    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.genres),
            joinedload(MovieModel.country),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages)
        )
        .order_by(desc(MovieModel.id))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    movies = result.scalars().unique().all()

    movies_data = [
        MovieDetailSchema.model_validate(m, from_attributes=True)
        for m in movies
    ]

    base_url = "/theater/movies/"
    prev_page = f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = f"{base_url}?page={page + 1}&per_page={per_page}" if page < total_pages else None

    return MovieListResponseSchema(
        movies=movies_data,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items
    )


@router.post(
    "/movies/",
    response_model=MovieListItemSchema,
    status_code=status.HTTP_201_CREATED
)
async def create_movie(movie: MovieCreateSchema, db: AsyncSession = Depends(get_db)):

    stmt = select(CountryModel).where(CountryModel.code == movie.country)
    country_obj = (await db.execute(stmt)).scalar_one_or_none()
    if not country_obj:
        country_obj = CountryModel(code=movie.country, name=movie.country)
        db.add(country_obj)
        await db.flush()

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country=country_obj
    )

    new_movie.genres = []
    for genre_name in movie.genres:
        genre = await db.scalar(select(GenreModel).where(GenreModel.name == genre_name))
        if not genre:
            genre = GenreModel(name=genre_name)
            db.add(genre)
            await db.flush()
        new_movie.genres.append(genre)

    new_movie.actors = []
    for actor_name in movie.actors:
        actor = await db.scalar(select(ActorModel).where(ActorModel.name == actor_name))
        if not actor:
            actor = ActorModel(name=actor_name)
            db.add(actor)
            await db.flush()
        new_movie.actors.append(actor)

    new_movie.languages = []
    for lang_name in movie.languages:
        language = await db.scalar(select(LanguageModel).where(LanguageModel.name == lang_name))
        if not language:
            language = LanguageModel(name=lang_name)
            db.add(language)
            await db.flush()
        new_movie.languages.append(language)

    existing_movie_stmt = select(MovieModel).where(
        MovieModel.name == movie.name,
        MovieModel.date == movie.date
    )
    existing_movie = (await db.execute(existing_movie_stmt)).scalar_one_or_none()

    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists."
        )

    db.add(new_movie)

    await db.flush()
    await db.commit()
    await db.refresh(new_movie)

    loaded_movie_result = await db.execute(
        select(MovieModel)
        .where(MovieModel.id == new_movie.id)
        .options(
            joinedload(MovieModel.genres),
            joinedload(MovieModel.country),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages)
        )
    )
    loaded_movie = loaded_movie_result.scalars().first()

    return MovieListItemSchema.model_validate(loaded_movie)


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie_details(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )
    movie = movie.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    return movie


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/")
async def update_movie_partial(
        movie_id: int,
        data: MoviePartialUpdateSchema,
        db: AsyncSession = Depends(get_db)
):

    movie = (await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))).scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found."
        )

    try:
        if data.name is not None:
            movie.name = data.name
        if data.date is not None:
            movie.date = data.date
        if data.score is not None:
            movie.score = data.score
        if data.overview is not None:
            movie.overview = data.overview
        if data.status is not None:
            movie.status = data.status
        if data.budget is not None:
            movie.budget = data.budget
        if data.revenue is not None:
            movie.revenue = data.revenue

        await db.commit()

    except Exception as e:
        await db.rollback()
        print(f"Помилка оновлення: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid input data or database error.")

    return {"detail": "Movie updated successfully."}
