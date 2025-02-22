import psutil
from pathlib import Path

def get_game_processes():
    """获取可能是游戏的进程列表"""
    # 系统进程黑名单
    system_processes = {
        'svchost.exe', 'csrss.exe', 'services.exe', 'lsass.exe', 'winlogon.exe',
        'smss.exe', 'spoolsv.exe', 'wininit.exe', 'RuntimeBroker.exe', 'SearchApp.exe',
        'SystemSettings.exe', 'TextInputHost.exe', 'SearchIndexer.exe'
    }

    # 游戏相关关键词
    game_keywords = [
        'game', 'unity', 'unreal', 'ue4', 'ue5', 'godot', 'cryengine',
        'directx', 'vulkan', 'opengl', 'steam', 'play', '游戏',
        'rpg', 'mmo', 'battle', 'fight', 'war', 'quest', 'raid',
        'arena', 'league', 'craft', 'world', 'dragon', 'sword',
        'racing', 'shooter', 'combat', 'strategy'
    ]

    # 游戏相关路径
    game_paths = [
        'games', 'steam', 'steamapps', 'program files (x86)', 'program files',
        'game', 'epic games', 'gog games', 'origin games', 'ubisoft',
        'netease', 'tencent', '腾讯游戏', '网易游戏', '完美世界', '盛趣游戏'
    ]

    # 游戏相关DLL
    game_dlls = [
        'd3d', 'xinput', 'unity', 'unreal', 'mono', 'physics',
        'havok', 'nvidia', 'amd', 'vulkan', 'opengl', 'directx',
        'steam_api', 'gameoverlayrenderer', 'fmod', 'cri'
    ]

    game_processes = []

    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            proc_info = proc.info
            if not proc_info['name'] or not proc_info['exe']:  # 跳过没有名称或路径的进程
                continue

            proc_name = proc_info['name'].lower()
            exe_path = Path(proc_info['exe']).resolve()

            # 跳过系统进程
            if proc_name in system_processes:
                continue

            # 检查是否可能是游戏进程
            is_game = False

            # 检查进程名称中是否包含游戏相关关键词
            if any(keyword in proc_name for keyword in game_keywords):
                is_game = True

            # 检查路径中是否包含游戏相关目录
            exe_path_str = str(exe_path).lower()
            if any(game_path in exe_path_str for game_path in game_paths):
                is_game = True

            # 检查是否包含游戏相关DLL
            try:
                if proc.memory_maps():
                    dlls = [m.path.lower() for m in proc.memory_maps() if m.path.endswith('.dll')]
                    if any(any(dll_name in dll for dll_name in game_dlls) for dll in dlls):
                        is_game = True
            except:
                pass

            # 如果进程名称不在黑名单中且内存大小超过特定值，也可能是游戏
            try:
                if proc.memory_info().rss > 100 * 1024 * 1024:  # 大于100MB
                    is_game = True
            except:
                pass

            # 如果是游戏进程或者不在黑名单中的普通进程，都添加到列表
            if is_game or (not any(sys_proc in proc_name for sys_proc in system_processes)):
                game_processes.append((proc_info['name'], proc_info['pid'], str(exe_path)))

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # 按进程名称排序（不区分大小写）
    game_processes.sort(key=lambda x: x[0].lower())
    return game_processes