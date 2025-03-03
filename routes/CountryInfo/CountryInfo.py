import os
import time
import unicodedata

import httpx
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, status

from Helper.formateDateOnTheBaseOfTheCountry import formateDateOnTheBaseOfTheCountry

load_dotenv(override=True)


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
def FetchAllTheCountry(order: str = Query("asc", alias="order")):
    try:
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

            return sortedData
        else:
            print(f"Error fetching country data: {response.status_code}")
            return []
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
async def GetCountryInfo(country: str = Query(..., alias="country")):

    try:
        username = "emilys"

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

        return {"success": True, "country": country, "states": state_array}
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
async def GetStateInfo(
    country: str = Query(..., alias="country"), state_code: str = Query(..., alias="state_code")
):
    try:
        username = "emilys"
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
        return {
            "success": True,
            "country": country,
            "states": state_code,
            "cities_array": cities_array,
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
async def getCountryFormats(country_name: str = Query(..., alias="country_code")):
    try:
        url = f"https://restcountries.com/v3.1/alpha/{country_name}"
        response = await fetch_data(url=url)

        resData = response[0]

        if not isinstance(response, list) or not resData or "status" in response:
            raise ValueError("country Not Found")

        timeZones = resData.get("timezones")
        country_code = resData.get("cca2")
        postalCode = resData.get("postalCode")

        country_date_formate = await formateDateOnTheBaseOfTheCountry(country_code)

        return {
            "success":True,
            "postal_code_formate": postalCode,
            "timeZones": timeZones,
            "country_date_formate": (
                country_date_formate.get("dateFormat")
                if country_date_formate.get("success")
                else country_date_formate.get("error")
            ),
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
async def fetchAllTheCountryData(order: str = Query("asc", alias="order")):
    try:
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
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Fetching The Country",
                "success": False,
                "error": str(e),
            },
        )
