from django.contrib import admin
from .models import TrafficSignal, TrafficLog, DetectionArea, VideoSource, SystemSettings, CongestionEvent, SignalTimingLog, JunctionSignals, TrafficData


# Register your models here.
admin.site.register(TrafficSignal)
admin.site.register(TrafficLog)
admin.site.register(DetectionArea)
admin.site.register(VideoSource)
admin.site.register(SystemSettings)
admin.site.register(CongestionEvent)
admin.site.register(SignalTimingLog)
admin.site.register(JunctionSignals)
admin.site.register(TrafficData)