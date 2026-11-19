
def remove_overlapping_detections(results):
    """
    Keep the highest-priority detection when
    multiple detected spans overlap.
    """

    sorted_results = sorted(
        results,
        key=lambda result: (
            -result.score,
            -(result.end - result.start),
            result.start,
            result.entity_type,
        ),
    )

    filtered = []

    for result in sorted_results:
        overlaps = any(
            result.start < existing.end
            and result.end > existing.start
            for existing in filtered
        )

        if not overlaps:
            filtered.append(result)

    return sorted(
        filtered,
        key=lambda result: (
            result.start,
            result.end,
        ),
    )
