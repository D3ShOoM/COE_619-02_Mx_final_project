# Generated for the campus shuttle demo.
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('route_id', models.CharField(max_length=32, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('color', models.CharField(default='#00843D', max_length=12)),
                ('total_length_m', models.FloatField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['route_id']},
        ),
        migrations.CreateModel(
            name='FeedEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('INFO', 'Info'), ('WARN', 'Warning'), ('ERROR', 'Error')], default='INFO', max_length=8)),
                ('component', models.CharField(default='system', max_length=64)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Bus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bus_id', models.CharField(max_length=32, unique=True)),
                ('label', models.CharField(max_length=120)),
                ('capacity', models.PositiveIntegerField(default=40)),
                ('current_occupancy', models.PositiveIntegerField(default=0)),
                ('occupancy_level', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')], default='LOW', max_length=12)),
                ('last_lat', models.FloatField(blank=True, null=True)),
                ('last_lon', models.FloatField(blank=True, null=True)),
                ('heading', models.FloatField(default=0)),
                ('speed_mps', models.FloatField(default=0)),
                ('progress_m', models.FloatField(default=0, help_text='Distance along loop from route origin.')),
                ('current_segment_index', models.PositiveIntegerField(default=0)),
                ('last_seen', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('demo_speed_mps', models.FloatField(default=4.8)),
                ('demo_phase', models.FloatField(default=0, help_text='Offset used by the simulator to make buses distinct.')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buses', to='shuttle.route')),
            ],
            options={'ordering': ['bus_id']},
        ),
        migrations.CreateModel(
            name='Stop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stop_id', models.CharField(max_length=32, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('sequence', models.PositiveIntegerField()),
                ('lat', models.FloatField()),
                ('lon', models.FloatField()),
                ('distance_m', models.FloatField(default=0, help_text='Distance along loop from route origin.')),
                ('is_active', models.BooleanField(default=True)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stops', to='shuttle.route')),
            ],
            options={'ordering': ['route', 'sequence'], 'unique_together': {('route', 'sequence')}},
        ),
        migrations.CreateModel(
            name='RouteShapePoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence', models.PositiveIntegerField()),
                ('lat', models.FloatField()),
                ('lon', models.FloatField()),
                ('distance_m', models.FloatField(default=0)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shape_points', to='shuttle.route')),
            ],
            options={'ordering': ['route', 'sequence'], 'unique_together': {('route', 'sequence')}},
        ),
        migrations.CreateModel(
            name='PositionPing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lat', models.FloatField()),
                ('lon', models.FloatField()),
                ('speed_mps', models.FloatField(default=0)),
                ('heading', models.FloatField(default=0)),
                ('progress_m', models.FloatField(default=0)),
                ('segment_index', models.PositiveIntegerField(default=0)),
                ('source', models.CharField(default='simulator', max_length=64)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='position_pings', to='shuttle.bus')),
            ],
            options={'ordering': ['-created_at'], 'indexes': [models.Index(fields=['bus', '-created_at'], name='shuttle_pos_bus_id_24005a_idx')]},
        ),
        migrations.CreateModel(
            name='OccupancyReading',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.PositiveIntegerField()),
                ('level', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')], max_length=12)),
                ('boardings', models.PositiveIntegerField(default=0)),
                ('alightings', models.PositiveIntegerField(default=0)),
                ('source', models.CharField(default='simulator', max_length=64)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='occupancy_readings', to='shuttle.bus')),
            ],
            options={'ordering': ['-created_at'], 'indexes': [models.Index(fields=['bus', '-created_at'], name='shuttle_occ_bus_id_9a2e83_idx')]},
        ),
        migrations.CreateModel(
            name='SegmentStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('segment_index', models.PositiveIntegerField()),
                ('distance_m', models.FloatField(default=0)),
                ('observed_travel_time_s', models.FloatField(default=90)),
                ('variance', models.FloatField(default=400)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('from_stop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='segments_from', to='shuttle.stop')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='segment_stats', to='shuttle.route')),
                ('to_stop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='segments_to', to='shuttle.stop')),
            ],
            options={'ordering': ['route', 'segment_index'], 'unique_together': {('route', 'segment_index')}},
        ),
    ]
