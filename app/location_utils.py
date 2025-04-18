# This function is no longer needed since we're using standardized location choices
# throughout the application. Keeping it for backward compatibility.
def map_form_location_to_member_location(form_location):
    """
    Maps a form location to the corresponding member location.

    Args:
        form_location (str): The location from a form (PTW or NHIS)

    Returns:
        str: The corresponding location used in the Member model
    """
    # With standardized location choices, the mapping is now 1:1
    return form_location


def validate_user_location_match(user_location, form_location):
    """
    Validates that the form location matches the user's assigned location.

    Args:
        user_location (str): The user's location from Member model
        form_location (str): The location from a form (PTW or NHIS)

    Returns:
        bool: True if locations match, False otherwise
    """
    if not user_location or not form_location:
        return True  # Skip validation if either location is not set

    # Debug print to help diagnose issues
    print(f"Validating locations: User location: {user_location}, Form location: {form_location}")

    # With standardized location choices, we can directly compare
    return form_location == user_location
