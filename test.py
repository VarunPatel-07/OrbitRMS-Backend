import json

import requests


# Function to get country details from REST Countries
def get_country_data():
    url = "https://restcountries.com/v3.1/all"
    response = requests.get(url)
    if response.status_code == 200:
        countries = response.json()
        country_data = []

        for country in countries:
            country_info = {
                "name": country.get("name", {}).get("common", "N/A"),
                "country_code": country.get("cca2", "N/A"),
                "dial_code": country.get("idd", {}).get("root", "N/A"),
                "flag": country.get("flags", {}).get("svg", "N/A"),
            }
            country_data.append(country_info)

        return country_data
    else:
        print(f"Error fetching country data: {response.status_code}")
        return []


# Function to get states and cities from GeoNames
def get_states_and_cities(country_name, geo_names_username, geo_names_password):
    # Fetch country info using GeoNames
    base_url = "http://api.geonames.org"
    country_info_url = f"{base_url}/countryInfoJSON"
    params = {
        "country": country_name,
        "username": geo_names_username,
        "password": geo_names_password,
    }
    response = requests.get(country_info_url, params=params)
    if response.status_code == 200:
        country_data = response.json()
        geonames_list = country_data.get("geonames", [])

        if not geonames_list:
            print(f"No GeoNames data found for {country_name}.")
            return []

        country_geoname_id = geonames_list[0].get("geonameId", None)

        if country_geoname_id:
            # Get states of the country
            states_url = f"{base_url}/childrenJSON"
            params = {
                "geonameId": country_geoname_id,
                "username": geo_names_username,
                "password": geo_names_password,
            }
            response = requests.get(states_url, params=params)
            if response.status_code == 200:
                states_data = response.json()
                states = states_data.get("geonames", [])

                states_info = []
                for state in states:
                    state_name = state.get("name", "N/A")
                    state_geoname_id = state.get("geonameId", None)
                    cities_info = []

                    if state_geoname_id:
                        # Get cities in the state
                        cities_url = f"{base_url}/searchJSON"
                        params = {
                            "geonameId": state_geoname_id,
                            "username": geo_names_username,
                            "password": geo_names_password,
                            "maxRows": 10,
                        }
                        response = requests.get(cities_url, params=params)
                        if response.status_code == 200:
                            cities_data = response.json()
                            cities = cities_data.get("geonames", [])
                            for city in cities:
                                cities_info.append(city.get("name", "N/A"))

                    states_info.append({"state": state_name, "cities": cities_info})
                return states_info
            else:
                print(f"Error fetching states: {response.status_code}")
        else:
            print("GeoNames country not found.")
    else:
        print(f"Error fetching country info: {response.status_code}")
    return []


# Main function to retrieve all country data
def main():
    geo_names_username = "emilys"  # GeoNames username
    geo_names_password = "emilys"  # GeoNames password

    print("Fetching country data...")
    countries = get_country_data()
    for country in countries:
        print(f"Country: {country['name']}")
        print(f"Country Code: {country['country_code']}")
        print(f"Dialing Code: {country['dial_code']}")
        print(f"Flag: {country['flag']}")

        print("Fetching states and cities...")
        states_and_cities = get_states_and_cities(
            country["country_code"], geo_names_username, geo_names_password
        )
        if states_and_cities:
            for state in states_and_cities:
                print(f"  State: {state['state']}")
                for city in state["cities"]:
                    print(f"    - City: {city}")
        else:
            print(f"No states and cities data available for {country['name']}.")


if __name__ == "__main__":
    main()
