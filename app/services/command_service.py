import subprocess
import os
import time
from typing import Optional, Tuple
from app.models.command import CommandResult

class CommandService:
    def __init__(self):
        self.current_directory = os.getcwd()
        self._command_history = []

    def execute_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        is_background: bool = False
    ) -> CommandResult:
        """
        执行shell命令
        """
        start_time = time.time()
        
        # 设置工作目录
        if working_directory:
            self.current_directory = working_directory
            
        try:
            # 准备命令执行环境
            env = os.environ.copy()
            
            # 执行命令
            if is_background:
                # 后台执行
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.current_directory,
                    env=env
                )
                output = "Command running in background with PID: " + str(process.pid)
                error = None
                exit_code = 0
            else:
                # 前台执行
                process = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=self.current_directory,
                    env=env
                )
                output = process.stdout
                error = process.stderr
                exit_code = process.returncode
                
            execution_time = time.time() - start_time
            
            # 创建执行结果
            result = CommandResult(
                command=command,
                output=output,
                error=error,
                exit_code=exit_code,
                execution_time=execution_time,
                working_directory=self.current_directory
            )
            
            # 添加到历史记录
            self._command_history.append(result)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            return CommandResult(
                command=command,
                output="",
                error=str(e),
                exit_code=1,
                execution_time=execution_time,
                working_directory=self.current_directory
            )
    
    def get_command_history(self) -> list[CommandResult]:
        """获取命令执行历史"""
        return self._command_history
        
    def change_directory(self, path: str) -> None:
        """更改当前工作目录"""
        full_path = os.path.abspath(os.path.join(self.current_directory, path))
        if os.path.exists(full_path) and os.path.isdir(full_path):
            self.current_directory = full_path
        else:
            raise ValueError(f"Invalid directory path: {path}")

command_service = CommandService() 