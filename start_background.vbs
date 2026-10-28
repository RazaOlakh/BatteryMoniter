' Battery Monitor Pro - 100% Silent Background Launcher (Zero Window Flash)
' Double-clicking this file starts Battery Monitor Pro with zero terminal window.

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strPyw = strDir & "\src\app_launcher.pyw"
strPy = strDir & "\src\app_launcher.py"

If FSO.FileExists(strPyw) Then
    WshShell.Run "pythonw """ & strPyw & """ --service", 0, False
Else
    WshShell.Run "pythonw """ & strPy & """ --service", 0, False
End If

Set WshShell = Nothing
Set FSO = Nothing
