import json
import os
import time
import unicodedata

import httpx
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, Request, status

from Database.CacheDatabase import cache_database
from Helper.formateDateOnTheBaseOfTheCountry import formateDateOnTheBaseOfTheCountry
from RateLimiting import limiter

load_dotenv(override=True)

API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")
GEONAME_API_USERNAME = os.getenv("GEONAME_API_USERNAME")


async def fetch_data(url, retries=3, timeout=20):
    async with httpx.AsyncClient() as client:
        for attempt in range(retries):
            try:
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "message": "Error Fetching Data",
                        "success": False,
                        "error": str(e),
                    },
                )


countryApiRouter = APIRouter(prefix="/app/v1/country-info", tags=["country"])


@countryApiRouter.get("/fetchAll", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchAllTheCountry(request: Request, order: str = Query("asc", alias="order")):
    try:
        cache_data_key = "AllCountryDataInfo"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)
            cached_sorted_data = sorted(
                cached_Data, key=lambda x: x["country_name"], reverse=(order.lower() == "desc")
            )
            return {"message": "Fetched Successfully", "success": True, "data": cached_sorted_data}

        REST_API_URL = os.getenv("REST_API_URL")

        response = requests.get(REST_API_URL)

        if response.status_code == 200:
            countryData = response.json()

            countryArray = []

            for country in countryData:
                global country_number_code
                if country.get("idd"):
                    root = country.get("idd").get("root", "")
                    suffixes = country.get("idd").get("suffixes", [])
                    if suffixes:
                        country_number_code = root + suffixes[0]
                    else:
                        country_number_code = root

                refinedObj = {
                    "country_name": country.get("name", {}).get("common", "N/A"),
                    "country_flag": country.get("flag", "N/A"),
                    "country_code": country.get("cca2"),
                    "country_number_code": country_number_code,
                }
                countryArray.append(refinedObj)

            sortedData = sorted(
                countryArray, key=lambda x: x["country_name"], reverse=(order.lower() == "desc")
            )

            await cache_database.set(cache_data_key, json.dumps(sortedData), ex=30 * 24 * 3600)
            return {
                "message": "Fetched Successfully",
                "success": True,
                "data": sortedData,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Error Accrued While Fetching The Country Contact Info",
                    "success": False,
                },
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Fetching The Country",
                "success": False,
                "error": str(e),
            },
        )


@countryApiRouter.get("/getCountryInfo", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def GetCountryInfo(
    request: Request,
    country: str = Query(..., alias="country"),
    order: str = Query("asc", alias="order"),
):

    try:
        cache_data_key = f"CountryDataFor-{country}"

        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_statesData = json.loads(cached_data)
            cached_reverse = order.lower() == "desc"
            cached_statesData.sort(key=lambda x: x["state_name"], reverse=cached_reverse)
            return {
                "message": "Fetched Successfully",
                "success": True,
                "data": {
                    "country": country,
                    "states": cached_statesData,
                },
            }

        username = GEONAME_API_USERNAME

        country_url = f"http://api.geonames.org/searchJSON?country={country}&featureCode=ADM1&username={username}"

        states_data = await fetch_data(country_url)

        if "geonames" not in states_data or not states_data["geonames"]:
            new_country_url = (
                f"http://api.geonames.org/searchJSON?country={country}&username={username}"
            )
            states_data = await fetch_data(new_country_url)

            if "geonames" not in states_data or not states_data["geonames"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "No states found for this country", "success": False},
                )

        states = states_data["geonames"]

        state_array = []
        for state in states:
            state_name = state["name"]
            state_code = state.get("adminCode1", "")

            formatted_state_name = ""

            if any(ord(char) > 127 for char in state_name):
                formatted_state_name = (
                    unicodedata.normalize("NFD", state_name)
                    .encode("ascii", "ignore")
                    .decode("utf-8")
                    .lower()
                )
            else:
                formatted_state_name = state_name.lower()

            state_array.append({"state_name": formatted_state_name, "state_code": state_code})

        reverse = order.lower() == "desc"
        state_array.sort(key=lambda x: x["state_name"], reverse=reverse)
        await cache_database.set(cache_data_key, json.dumps(state_array), ex=30 * 24 * 3600)

        return {
            "message": "Fetched Successfully",
            "success": True,
            "data": {
                "country": country,
                "states": state_array,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while fetching the state date of the country",
                "success": False,
                "error": str(e),
            },
        )


@countryApiRouter.get("/getStateInfo", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def GetStateInfo(
    request: Request,
    country: str = Query(..., alias="country"),
    state_code: str = Query(..., alias="state_code"),
    order: str = Query("asc", alias="order"),
):
    try:
        cached_data_key = f"cached_{state_code}_for_{country}"
        cached_data = await cache_database.get(cached_data_key)
        if cached_data:
            formatted_cached_data = json.loads(cached_data)
            cached_reverse = order.lower() == "desc"
            sorted_cached_data = sorted(formatted_cached_data, reverse=cached_reverse)
            return {
                "message": "Fetched Successfully",
                "success": True,
                "data": {
                    "country": country,
                    "states": state_code,
                    "cities_array": sorted_cached_data,
                },
            }

        username = GEONAME_API_USERNAME
        cities_url = f"http://api.geonames.org/searchJSON?adminCode1={state_code}&country={country}&featureClass=P&username={username}"

        cities_data = await fetch_data(cities_url)

        if "geonames" not in cities_data or not cities_data["geonames"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No city found for this state", "success": False},
            )
        cities = cities_data["geonames"]

        cities_array = []
        for city in cities:
            city_name = city["name"]
            formatted_city_name = ""

            if any(ord(char) > 127 for char in city_name):
                formatted_city_name = (
                    unicodedata.normalize("NFD", city_name)
                    .encode("ascii", "ignore")
                    .decode("utf-8")
                    .lower()
                )
            else:
                formatted_city_name = city_name.lower()
            cities_array.append(formatted_city_name)
        reverse = order.lower() == "desc"
        sorted_data = sorted(cities_array, reverse=reverse)
        await cache_database.set(cached_data_key, json.dumps(cities_array), ex=30 * 24 * 3600)
        return {
            "message": "Fetched Successfully",
            "success": True,
            "data": {
                "country": country,
                "states": state_code,
                "cities_array": sorted_data,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while fetching the state date of the country",
                "success": False,
                "error": str(e),
            },
        )


@countryApiRouter.get("/getFormats", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def getCountryFormats(request: Request, country_code: str = Query(..., alias="country-code")):
    try:
        cached_data_key = f"{country_code}_date_formate"
        cached_data = await cache_database.get(cached_data_key)
        if cached_data:
            formatted_cached_data = json.loads(cached_data)
            return {
                "message": "Fetched Successfully",
                "success": True,
                "data": {
                    "postal_code_formate": formatted_cached_data.get("postal_code_formate"),
                    "timeZones": formatted_cached_data.get("timeZones"),
                    "country_date_formate": formatted_cached_data.get("country_date_formate"),
                },
            }
        url = f"https://restcountries.com/v3.1/alpha/{country_code}"
        response = await fetch_data(url=url)

        resData = response[0]

        if not isinstance(response, list) or not resData or "status" in response:
            raise ValueError("country Not Found")

        timeZones = resData.get("timezones")
        country_code = resData.get("cca2")
        postalCode = resData.get("postalCode")

        country_date_formate = await formateDateOnTheBaseOfTheCountry(country_code)

        data = {
            "postal_code_formate": postalCode,
            "timeZones": timeZones,
            "country_date_formate": (
                country_date_formate.get("dateFormat")
                if country_date_formate.get("success")
                else country_date_formate.get("error")
            ),
        }

        await cache_database.set(cached_data_key, json.dumps(data), ex=30 * 24 * 3600)

        return {
            "message": "Fetched Successfully",
            "success": True,
            "data": {
                "postal_code_formate": postalCode,
                "timeZones": timeZones,
                "country_date_formate": (
                    country_date_formate.get("dateFormat")
                    if country_date_formate.get("success")
                    else country_date_formate.get("error")
                ),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while fetching the state date of the country",
                "success": False,
                "error": str(e),
            },
        )


@countryApiRouter.get("/fetchAllCountry", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def fetchAllTheCountryData(request: Request, order: str = Query("asc", alias="order")):
    try:
        cache_data_key = "AllCountryCachedDataKey"
        cache_data = await cache_database.get(cache_data_key)
        if cache_data:
            sorted_cached_data = json.loads(cache_data)
            cache_reverse = order.lower() == "desc"
            sorted_cached_data.sort(key=lambda x: x["country_name"], reverse=cache_reverse)

            return {"message": "Fetched Successfully", "success": True, "data": sorted_cached_data}

        url = os.getenv("REST_API_URL")

        response = await fetch_data(url=url)

        countryData = response

        data = []
        for country in countryData:

            postal_code = country.get("postalCode")
            default_postal_code = {
                "format": "##########",
                "regex": "^(\\d{10})$",
            }

            global country_number_code
            if country.get("idd"):
                root = country.get("idd").get("root", "")
                suffixes = country.get("idd").get("suffixes", [])
                if suffixes:
                    country_number_code = root + suffixes[0]
                else:
                    country_number_code = root
            obj = {
                "postal_code": postal_code if postal_code else default_postal_code,
                "country_name": country.get("name", {}).get("common", "N/A"),
                "country_code": country.get("cca2"),
                "country_flag": country.get("flag", "N/A"),
                "country_number_code": country_number_code,
            }

            data.append(obj)
        reverse = order.lower() == "desc"

        data.sort(key=lambda x: x["country_name"], reverse=reverse)

        await cache_database.set(cache_data_key, json.dumps(data), ex=30 * 24 * 3600)
        return {"message": "Fetched Successfully", "success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Fetching The Country",
                "success": False,
                "error": str(e),
            },
        )
