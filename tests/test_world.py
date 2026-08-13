from itertools import product
import unittest

from awakened_zero_rank.world import (
    MISSION_RANK_POINT_AWARDS,
    mission_rank_points_are_possible,
)


class MissionRankPointEvidenceTests(unittest.TestCase):
    def test_exact_composition_matches_authored_awards(self) -> None:
        for completed in range(6):
            possible = (
                {0} if completed == 0 else
                {sum(awards) for awards in product(
                    MISSION_RANK_POINT_AWARDS, repeat=completed)}
            )
            for points in range(0, completed * 17 + 2):
                self.assertEqual(
                    mission_rank_points_are_possible(completed, points),
                    points in possible,
                    (completed, points),
                )


if __name__ == "__main__":
    unittest.main()
