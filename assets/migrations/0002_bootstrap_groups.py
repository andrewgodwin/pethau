from django.contrib.auth.management import create_permissions
from django.db import migrations

FULL_ACCESS_MODELS = ["asset", "model", "assethistory"]
FULL_ACCESS_ACTIONS = ["view", "add", "change", "delete"]
VIEWER_MODELS = ["asset", "model", "assethistory"]


def _permission_codenames(models, actions):
    return [f"{action}_{model}" for model in models for action in actions]


def create_groups(apps, schema_editor):
    # Permission rows are normally created by a post_migrate signal that fires once
    # at the end of a full `migrate` run, so on a fresh database they don't exist yet
    # at this point in the migration graph. Create them explicitly instead.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    full_access_codenames = _permission_codenames(
        FULL_ACCESS_MODELS, FULL_ACCESS_ACTIONS
    )
    viewer_codenames = _permission_codenames(VIEWER_MODELS, ["view"])

    full_access = Group.objects.create(name="Full access")
    full_access.permissions.set(
        Permission.objects.filter(
            content_type__app_label="assets", codename__in=full_access_codenames
        )
    )

    viewer = Group.objects.create(name="Viewer")
    viewer.permissions.set(
        Permission.objects.filter(
            content_type__app_label="assets", codename__in=viewer_codenames
        )
    )


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Full access", "Viewer"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
