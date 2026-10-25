"""What the Flight agent asks the language model."""

ROLE = "You are the flight planner of a travel planning service."


def task(request):
    return (
        "Suggest two or three round-trip flight options for this trip, "
        f"with an estimated total fare for all travellers in {request.currency}."
    )
