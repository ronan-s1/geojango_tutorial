from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from . import models
from django.shortcuts import render
from django.apps import apps
from .models import Profile, Landmark
from bs4 import BeautifulSoup
import requests
from datetime import datetime

@login_required
def update_location(request):
    try:
        # getting user profile and there's none raise an error
        user_profile = models.Profile.objects.get(user=request.user)
        if not user_profile:
            raise ValueError("Can't get User details")

        # getting data from request
        point = request.POST["point"].split(",")
        description = request.POST["description"]
        lon_lat = [float(part) for part in point]
        lon, lat = lon_lat
        map_point = Point(lon_lat, srid=4326)

        # checking if they all have data
        if not all([lon, lat, description, point, map_point]):
            return JsonResponse({"message": "Not all fields have data"}, status=400)

        # saving data to db
        user_profile.lon = lon
        user_profile.lat = lat
        user_profile.location = map_point
        user_profile.description = f"Your current favourite landmark is {description}"
        user_profile.save()
        return JsonResponse({"message": f"Set location to lon: {lon}, lat: {lat}."}, status=200)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)


@login_required
def get_weather(request):
    url = "https://www.met.ie/forecasts/dublin"
    response = requests.get(url)

    # Default
    today_date = "No forecast today."
    today_forecast_text = "-"

    if response.status_code == 200:
        # Parse html and find all h2 tags on the page
        soup = BeautifulSoup(response.text, "html.parser")
        all_h2_tags = soup.find_all("h2")

        # Find the h2 tag that contains "TODAY"
        today_h2 = next((h2 for h2 in all_h2_tags if "TODAY" in h2.text), None)

        if today_h2:
            today_date = today_h2.get_text(strip=True).split(" - ")[1]
            today_forecast_text = today_h2.find_next("p").get_text(strip=True)
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    return JsonResponse({
        "weather_date": today_date,
        "weather_forecast": today_forecast_text,
    })


@login_required
def map_view(request):
    # lazy import to avoid circular import
    user_profile = Profile.objects.get(user=request.user)
    landmark_model = apps.get_model("userlocation", "Landmark")
    landmarks = landmark_model.objects.all()
    return render(request, "map.html", {
        "landmarks": landmarks,
        "favorite_location": user_profile.description,
        "last_updated": user_profile.last_updated
    })


@login_required
def get_favourite_location(request):
    # lazy import to avoid circular import
    user_profile = Profile.objects.get(user=request.user)
    return JsonResponse({
        "favourite_location": user_profile.description,
        "last_updated": user_profile.last_updated
    })


@login_required
def add_landmark(request):
    try:
        longitude = float(request.POST.get("longitude"))
        latitude = float(request.POST.get("latitude"))
        description = request.POST.get("description")
        category = request.POST.get("category")
        map_point = Point((longitude, latitude), srid=4326)

        # backend error checking
        if not all([longitude, latitude, description, category, map_point]):
            return JsonResponse({"message": "Not all fields have data"}, status=400)

        landmark = Landmark(
            latitude=latitude,
            longitude=longitude,
            description=description,
            location=map_point,
            category=category
        )
        landmark.save()
        return JsonResponse({"message": f"Success: {description}, {latitude}, {longitude}, {category}"}, status=200)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)
