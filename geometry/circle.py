import math
from random import randint
from typing import List, Tuple

import matplotlib.pyplot as plt
from shapely.geometry import Polygon

from geometry.coord import Coord
from geometry.entity import Entity
from geometry.geometric import calculate_directional_angle_of_line, calculate_points_in_distance_on_circle
from geometry.path import Path
from geometry.segment import Segment

INF = 1000


class Circle(Entity):
    BUFFER_RESOLUTION = 40
    ANGLE_STEP = math.pi / BUFFER_RESOLUTION
    EPSILON = 1

    def __init__(self, center: Coord, radius: float) -> None:
        self._center = center
        self._radius = radius
        self._inner_polygon = center.to_shapely.buffer(radius, resolution=Circle.BUFFER_RESOLUTION)
        self._outer_polygon = center.to_shapely.buffer(radius + Circle.EPSILON, resolution=Circle.BUFFER_RESOLUTION)
        self._boundary = None

    @property
    def center(self) -> Coord:
        return self._center

    @property
    def radius(self) -> float:
        return self._radius

    @property
    def perimeter(self) -> float:
        return 2 * math.pi * self._radius

    @property
    def inner_polygon(self) -> Polygon:
        return self._inner_polygon

    @property
    def outer_polygon(self) -> Polygon:
        return self._outer_polygon

    @property
    def to_shapely(self) -> Polygon:
        return self._inner_polygon

    def contains(self, coord: Coord) -> bool:
        return coord.distance_to(self.center) <= self.radius

    def path_intersection_length(self, path: Path) -> float:
        return sum([self.inner_polygon.intersection(segment.to_shapely).length for segment in path.segments])

    def calculate_exit_point(self, start: Coord, chord: float, target: Coord) -> Coord:
        if chord >= self.radius * 2:
            return start.shifted(distance=2 * self.radius, angle=Segment(start, self.center).angle)

        return min(calculate_points_in_distance_on_circle(self.center, self.radius, start, chord),
                   key=lambda p: p.distance_to(target))

    @property
    def boundary(self) -> List[Coord]:
        if self._boundary is None:
            X, Y = self.outer_polygon.exterior.coords.xy
            self._boundary = [Coord(x, y) for x, y in zip(list(X), list(Y))]
        return self._boundary

    def arc_length_between(self, start: Coord, end: Coord) -> float:
        angle1 = calculate_directional_angle_of_line(start=self.center, end=start)
        angle2 = calculate_directional_angle_of_line(start=self.center, end=end)

        return abs(angle1 - angle2) * self.radius

    def get_boundary_between(self, start: Coord, end: Coord) -> List[Coord]:
        angle1 = calculate_directional_angle_of_line(start=self.center, end=start)
        angle2 = calculate_directional_angle_of_line(start=self.center, end=end)

        small_angle = min(angle1, angle2)
        great_angle = max(angle1, angle2)

        boundary = []

        # if shorter boundary is counterclockwise
        if great_angle - small_angle <= math.pi:
            angle = small_angle
            while angle < great_angle:
                boundary.append(self.center.shifted(self.radius + Circle.EPSILON, angle))
                angle += Circle.ANGLE_STEP
            boundary.append(self.center.shifted(self.radius + Circle.EPSILON, great_angle))

        # if shorter boundary is clockwise
        else:
            angle = great_angle
            while angle < small_angle + 2 * math.pi:
                boundary.append(self.center.shifted(self.radius + Circle.EPSILON, angle))
                angle += Circle.ANGLE_STEP
            boundary.append(self.center.shifted(self.radius + Circle.EPSILON, small_angle))

        return boundary[::-1] if not boundary[0].distance_to(start) < boundary[0].distance_to(end) else boundary

    @classmethod
    def generate_random_threat(cls, environment_range: Tuple[int, int], radius_range: Tuple[int, int] = (100, 200)) \
            -> 'Circle':
        rand_radius = randint(*radius_range)
        x_range, y_range = environment_range
        rand_center = Coord(randint(rand_radius, x_range - rand_radius), randint(rand_radius, y_range - rand_radius))
        return Circle(center=rand_center, radius=rand_radius)

    @classmethod
    def generate_non_intersecting_random_circle(cls, circles: List['Circle'],
                                                environment_range: Tuple[int, int],
                                                radius_range: Tuple[int, int] = (50, 150)) -> 'Circle':
        # used radius range of (25, 75) for the 50 circles experiment
        new_circle = None

        is_intersecting = True
        while is_intersecting:
            is_intersecting = False
            new_circle = Circle.generate_random_threat(environment_range, radius_range)

            for circle in circles:
                if circle.to_shapely.buffer(5).intersects(new_circle.to_shapely.buffer(5)):
                    is_intersecting = True
                    break

        return new_circle

    @classmethod
    def calculate_partition_between_circles(cls, circle1: 'Circle', circle2: 'Circle', source: Coord, target: Coord,
                                            all_circles: List['Circle']) -> Segment:
        # find inf partition
        center1, center2 = circle1.center, circle2.center
        radius1, radius2 = circle1.radius, circle2.radius

        centers_segment = Segment(center1, center2)
        centers_distance = centers_segment.length
        centers_angle = centers_segment.angle

        point_between = center1.shifted((radius1 + (centers_distance - radius2)) / 2, centers_angle)
        inf_partition = Segment(
            point_between.shifted(INF, centers_angle + 0.5 * math.pi),
            point_between.shifted(INF, centers_angle - 0.5 * math.pi)
        )

        # find convex hull of all entities in the environment
        all_shapely_points = [source.xy, target.xy]
        for circle in all_circles:
            all_shapely_points += circle.to_shapely.boundary.coords
        convex_hull = Polygon(all_shapely_points).convex_hull

        # return the truncated partition
        intersection_points = convex_hull.intersection(inf_partition.to_shapely).coords
        return Segment(Coord(*intersection_points[0]), Coord(*intersection_points[1]))

    def plot(self, color: str = 'red') -> None:
        plt.plot([p.x for p in self.boundary], [p.y for p in self.boundary], color=color, zorder=1)
        plt.scatter(self.center.x, self.center.y, s=20, color='black', zorder=1)
        plt.scatter(self.center.x, self.center.y, s=10, color=color, zorder=2)

    def __str__(self) -> str:
        return f'Circle({self.center},{self.radius})'
