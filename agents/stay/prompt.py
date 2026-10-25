"""What the Stay agent asks the language model."""

ROLE = "You are the accommodation planner of a travel planning service."


def task(request):
    return (
        "Suggest two or three places to stay for the whole trip, in different areas or price ranges, "
        f"with an estimated total price for all nights and travellers in {request.currency}."
    )
