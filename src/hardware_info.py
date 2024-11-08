#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# SystemMonitor モジュール

#######################################################################################
# import処理
## 標準ライブラリ
import re
import time

## pypiライブラリ
import psutil
import wmi

## その他
import clr
clr.AddReference('System.Diagnostics.Process')
clr.AddReference('System.Collections')
import System.Diagnostics as Diagnostics  # type: ignore
from System.Collections.Generic import List  # type: ignore

#######################################################################################
# 定数
CPU_NAME = None
MEM_INFO = None

#######################################################################################
# 変数


#######################################################################################
# 関数


#######################################################################################
# クラス
class SystemMonitor:
    """
    システムのリソース使用状況を監視するクラス。

    CPU、メモリ、ディスク、ネットワーク、GPUなどの使用率を取得する機能を提供します。
    また、システムのハードウェア情報（CPU名、メモリ情報など）も取得できます。
    """
    def __init__(self):
        """
        SystemMonitorの初期化を行うコンストラクタ。
        
        Attributes:
            wmi (WMI): WMIインスタンスを保持。
            GPU_Engines (List or None): GPUエンジンのパフォーマンスカウンタを格納するリスト。初期値はNone。
        """
        self.wmi = wmi.WMI()
        self.GPU_Engines = None

    def get_cpu_usage(self):
        """
        CPU使用率を取得する関数。
        
        Returns:
            float: CPUの平均使用率（パーセンテージ）。
        """
        all_core = psutil.cpu_percent(interval=None, percpu=True)
        return sum(all_core) / len(all_core) if all_core else None

    def get_memory_usage(self):
        """
        メモリ使用率を取得する関数。
        
        Returns:
            float: メモリの使用率（パーセンテージ）。
        """
        memory_info = psutil.virtual_memory()
        return memory_info.percent

    def get_disk_usage(self):
        """
        ディスク使用率を取得する関数。
        
        Returns:
            float: ディスクの使用率（パーセンテージ）。
        """
        disk_usage = psutil.disk_usage('/')
        return disk_usage.percent

    def get_network_usage(self):
        """
        ネットワーク使用量を取得する関数。
        
        Returns:
            dict: 送信バイト数と受信バイト数を含む辞書。
        """
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv
        }

    def get_cpu_name(self):
        """
        CPU名を取得する関数。
        
        Returns:
            str: CPU名。取得に失敗した場合は例外メッセージを返す。
        """
        try:
            if CPU_NAME:
                return CPU_NAME
            cpu = self.wmi.Win32_Processor()[0]
            return cpu.Name.replace("(TM)", "™").replace("(R)", "®").replace(" with Radeon Graphics", "")
        except Exception as e:
            return str(e)

    def get_memory_info(self):
        """
        メモリの詳細情報を取得する関数。
        
        Returns:
            list: メモリモジュールごとの詳細情報を含む辞書のリスト。
        """
        try:
            memory_modules = self.wmi.Win32_PhysicalMemory()
            memory_info = []
            for module in memory_modules:
                info = {
                    "Capacity": int(module.Capacity) // (1024 ** 3),  # GBに変換
                    "Speed": module.Speed,
                    "Manufacturer": module.Manufacturer,
                    "PartNumber": module.PartNumber
                }
                memory_info.append(info)
            return memory_info
        except Exception as e:
            return str(e)

    def get_total_memory_info(self):
        """
        メモリ全体の情報を取得する関数。
        
        Returns:
            dict: メモリの総容量、モジュール数、最小速度を含む辞書。
        """
        try:
            if MEM_INFO:
                return MEM_INFO
            memory_modules = self.wmi.Win32_PhysicalMemory()
            total_capacity = sum(int(module.Capacity) for module in memory_modules) // (1024 ** 3)
            num_modules = len(memory_modules)
            min_speed = min(int(module.Speed) for module in memory_modules)

            return {
                "TotalCapacity": total_capacity,  # GB
                "NumModules": num_modules,
                "MinSpeed": min_speed  # MHz
            }
        except Exception as e:
            return str(e)

    def get_cpu_core_count(self):
        """
        CPUの物理コア数を取得する関数。
        
        Returns:
            int: 物理コア数。
        """
        return psutil.cpu_count(logical=False)

    def get_cpu_thread_count(self):
        """
        CPUのスレッド数を取得する関数。
        
        Returns:
            int: スレッド数。
        """
        return psutil.cpu_count(logical=True)
    
    def get_gpu_counters(self):
        """
        GPUのパフォーマンスカウンタを取得する関数。
        
        Returns:
            List[Diagnostics.PerformanceCounter]: GPUエンジンのパフォーマンスカウンタのリスト。
        """
        category = Diagnostics.PerformanceCounterCategory('GPU Engine')
        ret = List[Diagnostics.PerformanceCounter]()
        for cat_name in category.GetInstanceNames():
            if re.findall(r'engtype_3D', cat_name):
                ret.Add(category.GetCounters(cat_name)[-1])
        return ret

    def gpu_usage(self):
        """
        GPU使用率を計算する関数。
        
        Returns:
            float: GPUの平均使用率（パーセンテージ）。
        """
        if not self.GPU_Engines:
            self.GPU_Engines = self.get_gpu_counters()
            _ = [x.NextValue() for x in self.GPU_Engines]  # 初期化
            time.sleep(1)
        return sum(gpu.NextValue() for gpu in self.GPU_Engines) / len(self.GPU_Engines)

buffer_instance = SystemMonitor()
CPU_NAME = buffer_instance.get_cpu_name()
MEM_INFO = buffer_instance.get_total_memory_info()

#######################################################################################
# モジュールテスト用処理
if __name__ == "__main__":
    
    monitor = SystemMonitor()
    
    print(f"CPU Name: {monitor.get_cpu_name()}")
    print(f"CPU Usage: {monitor.get_cpu_usage()}%")
    print(f"Memory Usage: {monitor.get_memory_usage()}%")
    print(f"Disk Usage: {monitor.get_disk_usage()}%")
    # print(f"GPU Usage: {monitor.gpu_usage()}%")
    
    network_usage = monitor.get_network_usage()
    print(f"Network Usage - Bytes Sent: {network_usage['bytes_sent']} Bytes Received: {network_usage['bytes_recv']}")
    
    memory_info = monitor.get_memory_info()
    for i, mem in enumerate(memory_info, 1):
        print(f"Memory Module {i}:")
        print(f"  Capacity: {mem['Capacity']} GB")
        print(f"  Speed: {mem['Speed']} MHz")
        print(f"  Manufacturer: {mem['Manufacturer']}")
        print(f"  Part Number: {mem['PartNumber']}")
    
    total_memory_info = monitor.get_total_memory_info()
    print(f"Total Memory Capacity: {total_memory_info['TotalCapacity']} GB")
    print(f"Number of Memory Modules: {total_memory_info['NumModules']}")
    print(f"Minimum Memory Speed: {total_memory_info['MinSpeed']} MHz")
    
    print(f"CPU Core Count: {monitor.get_cpu_core_count()}")
    print(f"CPU Thread Count: {monitor.get_cpu_thread_count()}")
