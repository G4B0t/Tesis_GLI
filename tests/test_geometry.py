from gli.geometry import gas_bubble_area, liquid_film_area, tubing_area


def test_liquid_film_area_is_tubing_minus_bubble():
    tubing_diameter = 0.0603
    film_thickness = 0.001

    total = tubing_area(tubing_diameter)
    bubble = gas_bubble_area(tubing_diameter, film_thickness)
    film = liquid_film_area(tubing_diameter, film_thickness)

    assert abs(total - bubble - film) < 1.0e-12
