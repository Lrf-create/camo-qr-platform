from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command


def test_seed_demo_users_creates_repeatable_original_test_accounts(db, tmp_path):
    import csv
    import secrets
    password = secrets.token_urlsafe(24)
    seed_file = tmp_path / "demo_users.csv"
    with seed_file.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["username", "password", "is_staff", "is_superuser", "is_active"])
        for username in ["port_a_admin", "port_b_admin"]:
            writer.writerow([username, password, "true", "true", "true"])
    call_command("seed_demo_users", seed_file=str(seed_file), verbosity=0)
    call_command("seed_demo_users", seed_file=str(seed_file), verbosity=0)

    User = get_user_model()
    users = {
        user.username: user
        for user in User.objects.filter(username__in=["port_a_admin", "port_b_admin"])
    }

    assert set(users) == {"port_a_admin", "port_b_admin"}
    assert users["port_a_admin"].is_staff is True
    assert users["port_a_admin"].is_superuser is True
    assert users["port_a_admin"].is_active is True
    assert users["port_b_admin"].is_staff is True
    assert users["port_b_admin"].is_superuser is True
    assert users["port_b_admin"].is_active is True
    assert authenticate(username="port_a_admin", password=password) is not None
    assert authenticate(username="port_b_admin", password=password) is not None
