' 创建WScript.Shell对象，用于执行系统命令
Set WshShell = CreateObject("WScript.Shell")
' 创建WScript.Shell对象，用于文件和文件夹操作
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取VBScript所在目录（现在是scripts文件夹）
scriptsDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptsDir

' 执行startup.bat，完全隐藏窗口
WshShell.Run "cmd /c startup.bat", 0, False