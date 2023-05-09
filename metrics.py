import time
import atexit
import argparse
import psutil
import datetime
import socket
import getpass
import docker
from jtop import jtop, JtopException
from prometheus_client.core import InfoMetricFamily, GaugeMetricFamily, REGISTRY, CounterMetricFamily
from prometheus_client import start_http_server

with open('/etc/hostname', 'r') as file:
    HOSTNAME = file.read().strip()

# a = dict((len(container.image), container.image.tags[0].split("/")[1]) for container in client.containers.list())

class CustomCollector(object):
    def __init__(self):
        atexit.register(self.cleanup)
        self._jetson = jtop()
        self._jetson.start()
        self.psutil = psutil
        # self._docker = a

    def cleanup(self):
        print("Closing jetson-stats connection...")
        self._jetson.close()

    def collect(self):
        if self._jetson.ok():
            #
            # Board info
            #
            i = InfoMetricFamily('jetson_info_board', 'Board sys info', labels=['board_info'])
            i.add_metric(['info'], {
                # 'machine': self._jetson.board['info']['machine'],
                'jetpack': self._jetson.board['hardware']['Jetpack'],
                'l4t': self._jetson.board['hardware']['L4T'],
                'username': getpass.getuser(),
                # 'hostname': socket.gethostname()
                'hostname': HOSTNAME
                })
            yield i

            i = InfoMetricFamily('jetson_info_hardware', 'Board hardware info', labels=['board_hw'])
            i.add_metric(['hardware'], {
                'module': self._jetson.board['hardware']['Model'],
                'serial_number': self._jetson.board['hardware']['Serial Number'],
                })
            yield i


            #
            # NV Power Mode
            #
            i = InfoMetricFamily('jetson_nvpmode', 'NV power mode', labels=['nvpmode'])
            i.add_metric(['mode'], {'mode': self._jetson.nvpmodel.name})
            yield i

            #
            # Docker Images
            #
            # i = InfoMetricFamily('docker_image', 'tags', labels=['docker'])
            # i.add_metric(['tags'], {'container_1': self._docker['1'],})
            # yield i

            #
            # System Uptime
            #
            g = GaugeMetricFamily('jetson_uptime', 'System uptime', labels=['uptime'])
            days = self._jetson.uptime.days
            seconds = self._jetson.uptime.seconds
            hours = seconds//3600
            minutes = (seconds//60) % 60
            last_reboot = psutil.boot_time()
            g.add_metric(['days'], days)
            g.add_metric(['hours'], hours)
            g.add_metric(['minutes'], minutes)
            yield g

            #
            # Disk Usage
            #
            g = GaugeMetricFamily('jetson_usage_disk', 'Disk space usage', labels=['disk'])
            g.add_metric(['free'], self.psutil.disk_usage("/data").free /10**9)
            g.add_metric(['total'], self.psutil.disk_usage("/data").total /10**9)
            g.add_metric(['used'], self.psutil.disk_usage("/data").used /10**9)
            g.add_metric(['percent'], self.psutil.disk_usage("/data").percent)
            yield g

            g = GaugeMetricFamily('jetson_usage_rootdisk', 'Disk space usage-root', labels=['root'])
            g.add_metric(['total'], self._jetson.disk['total'])
            g.add_metric(['used'], self._jetson.disk['used'])
            g.add_metric(['available'], self._jetson.disk['available'])
            yield g

            # #
            # # CPU Usage
            # #
            # g = GaugeMetricFamily('jetson_usage_cpu', 'CPU % schedutil', labels=['cpu'])
            # g.add_metric(['cpu_1'], self._jetson.cpu['cpu'][0])
            # g.add_metric(['cpu_2'], self._jetson.cpu['cpu'][1])
            # g.add_metric(['cpu_3'], self._jetson.cpu['cpu'][2])
            # g.add_metric(['cpu_4'], self._jetson.cpu['cpu'][3])
            # g.add_metric(['cpu_5'], self._jetson.cpu['cpu'][4])
            # g.add_metric(['cpu_6'], self._jetson.cpu['cpu'][5])
            # yield g

            # #
            # # GPU Usage
            # #
            # g = GaugeMetricFamily('jetson_usage_gpu', 'GPU % schedutil', labels=['gpu'])
            # g.add_metric(['val'], self._jetson.gpu[1]['val'])
            # g.add_metric(['frq'], self._jetson.gpu[1]['frq'])
            # g.add_metric(['min_freq'], self._jetson.gpu[1]['min_freq'])
            # g.add_metric(['max_freq'], self._jetson.gpu[1]['max_freq'])
            # yield g

            # #
            # # RAM Usage
            # #
            # g = GaugeMetricFamily('jetson_usage_ram', 'Memory usage', labels=['ram'])
            # g.add_metric(['used'], self._jetson.ram['use'])
            # g.add_metric(['total'], self._jetson.ram['tot'])
            # yield g

            #
            # Fan Usage
            #
            g = GaugeMetricFamily('jetson_usage_fan', 'Fan usage', labels=['fan'])
            g.add_metric(['speed'], self._jetson.fan['tegra_pwmfan']['speed'][0])
            yield g

            #
            # Sensor Temperatures
            #
            g = GaugeMetricFamily('jetson_temperatures', 'Sensor temperatures', labels=['temperature'])
            g.add_metric(['gpu'], self._jetson.temperature['GPU']['temp'] if 'GPU' in self._jetson.temperature else 0)
            g.add_metric(['cpu'], self._jetson.temperature['BCPU']['temp'] if 'BCPU' in self._jetson.temperature else 0)
            yield g

            #
            # Power Usage
            #
            g = GaugeMetricFamily('jetson_usage_power', 'Power usage', labels=['power'])
            g.add_metric(['soc'], self._jetson.power['tot']['avg'] if 'tot' in self._jetson.power else 0)
            yield g



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=9000, help='Metrics collector port number')

    args = parser.parse_args()

    start_http_server(args.port)
    REGISTRY.register(CustomCollector())
    while True:
        time.sleep(1)