import os
import time
import httpx

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, status

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No states found for this country", "success": False},
            )

        states = states_data["geonames"]

        state_array = []
        for state in states:
            state_name = state["name"]
            state_code = state.get("adminCode1", "")
            state_array.append({"state_name": state_name, "state_code": state_code})

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
            cities_array.append(city["name"])
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
