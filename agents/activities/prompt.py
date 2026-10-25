"""What the Activities agent asks the language model."""

ROLE = "You are the activities planner of a travel planning service."


def task(request):
    # The traveller's preferences, or general sightseeing when none are given (TP-SRS-076).
    interests = ", ".join(request.preferences) if request.preferences else "general sightseeing"
    return (
        "Suggest two or three activities for this trip that match these interests: "
        f"{interests}. Give an estimated price per group in {request.currency}; use 0 for free activities."
    )
