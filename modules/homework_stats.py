GRADE_MAP = {
    "A+": 98,
    "A": 95,
    "A-": 92,
    "B+": 88,
    "B": 85,
    "B-": 82,
    "C+": 78,
    "C": 75,
    "C-": 72,
    "D": 65,
    "F": 50
}


def calculate_homework_statistics(df):

    if df.empty:
        return {
            "average": 0,
            "highest": 0,
            "lowest": 0,
            "trend": 0
        }


    scores = (
        df["grade"]
        .map(GRADE_MAP)
        .dropna()
    )


    if scores.empty:

        return {
            "average": 0,
            "highest": 0,
            "lowest": 0,
            "trend": 0
        }


    average = scores.mean()

    highest = scores.max()

    lowest = scores.min()


    # Compare recent vs older performance

    if len(scores) >= 2:

        midpoint = len(scores)//2

        old_average = (
            scores.iloc[:midpoint]
            .mean()
        )

        new_average = (
            scores.iloc[midpoint:]
            .mean()
        )

        trend = new_average - old_average

    else:

        trend = 0


    return {
        "average": round(average,1),
        "highest": round(highest,1),
        "lowest": round(lowest,1),
        "trend": round(trend,1)
    }
