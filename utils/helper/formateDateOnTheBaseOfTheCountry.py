import re

from babel.dates import get_date_format

from constants.countryLocaleMapping import country_locale_mapping, dependent_date_format


def get_locale_from_country_code(country_code):
    """Returns the correct locale string based on a country code."""

    if country_code in country_locale_mapping:
        return country_locale_mapping[country_code]


def get_dependent_country_info(country_code):
    for dependent_country in dependent_date_format:
        if country_code in dependent_country:
            country = dependent_country[country_code]
            date_format = country.get("date_format")
            return date_format


def get_default_separator(country_code):
    """Defines the default separator based on country."""
    separator_mapping = {
        "US": "/",  # 12/31/2024 (MM/DD/YYYY)
        "IN": "-",  # 31-12-2024 (DD-MM-YYYY)
        "PK": "-",  # 31-12-2024 (DD-MM-YYYY)
        "RU": ".",  # 31.12.2024 (DD.MM.YYYY)
        "FR": "/",  # 31/12/2024 (DD/MM/YYYY)
        "DE": ".",  # 31.12.2024 (DD.MM.YYYY)
        "JP": "/",  # 2024/12/31 (YYYY/MM/DD)
        "CN": "-",  # 2024-12-31 (YYYY-MM-DD)
        "ES": "/",  # 31/12/2024 (DD/MM/YYYY)
        "IT": "/",  # 31/12/2024 (DD/MM/YYYY)
        "BR": "/",  # 31/12/2024 (DD/MM/YYYY)
        "MX": "/",  # 31/12/2024 (DD/MM/YYYY)
        "CA": "/",  # 2024/12/31 or 31/12/2024 (YYYY/MM/DD or DD/MM/YYYY, varies)
        "AU": "/",  # 31/12/2024 (DD/MM/YYYY)
        "UK": "/",  # 31/12/2024 (DD/MM/YYYY)
        "ZA": "/",  # 31/12/2024 (DD/MM/YYYY)
        "NG": "/",  # 31/12/2024 (DD/MM/YYYY)
        "KE": "/",  # 31/12/2024 (DD/MM/YYYY)
        "ID": "-",  # 31-12-2024 (DD-MM-YYYY)
        "MY": "-",  # 31-12-2024 (DD-MM-YYYY)
        "SG": "/",  # 31/12/2024 (DD/MM/YYYY)
        "PH": "/",  # 12/31/2024 (MM/DD/YYYY, similar to US)
        "TH": "-",  # 31-12-2024 (DD-MM-YYYY)
        "VN": "/",  # 31/12/2024 (DD/MM/YYYY)
        "KR": ".",  # 2024.12.31 (YYYY.MM.DD)
        "HK": "/",  # 31/12/2024 (DD/MM/YYYY)
        "TW": "/",  # 2024/12/31 (YYYY/MM/DD)
        "AR": "/",  # 31/12/2024 (DD/MM/YYYY)
        "CL": "/",  # 31/12/2024 (DD/MM/YYYY)
        "CO": "/",  # 31/12/2024 (DD/MM/YYYY)
        "PE": "/",  # 31/12/2024 (DD/MM/YYYY)
        "SA": "/",  # 31/12/2024 (DD/MM/YYYY)
        "AE": "/",  # 31/12/2024 (DD/MM/YYYY)
        "IR": "-",  # 1402-10-10 (Persian Calendar)
        "IL": ".",  # 31.12.2024 (DD.MM.YYYY)
    }

    return separator_mapping.get(country_code, "-")  # Default to "-"


async def formateDateOnTheBaseOfTheCountry(country_code):
    try:
        locale = get_locale_from_country_code(country_code)

        if not locale:
            date_format = get_dependent_country_info(country_code)
            if not date_format:
                return {"success": False, "error": "Invalid country code"}
            else:
                return {"success": True, "dateFormat": date_format}
        date_format = get_date_format(locale=locale).pattern

        separator = get_default_separator(country_code)

        date_format = re.sub(r"[^dMy ]", "", date_format)

        # Replace date format characters with readable words
        date_format = date_format.replace("yyyy", "YYYY").replace("yy", "YY").replace("y", "Y")
        date_format = (
            date_format.replace("MMMM", "MMMM")
            .replace("MMM", "MMM")
            .replace("MM", "MM")
            .replace("M", "M")
        )
        date_format = date_format.replace("dd", "DD").replace("d", "DD")

        return {"success": True, "dateFormat": separator.join(date_format.split())}
    except Exception as e:
        return {"success": False, "error": str(e)}
