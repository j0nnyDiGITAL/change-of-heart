Set WshShell = CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut("C:\Users\kufis\Desktop\P5R Save Editor.lnk")
Shortcut.TargetPath = "E:\ai-workspace\knowledge-base\projects\p5r-save-editor\P5R_Save_Editor.vbs"
Shortcut.WorkingDirectory = "E:\ai-workspace\knowledge-base\projects\p5r-save-editor"
Shortcut.Description = "Persona 5 Royal Steam Save Editor"
Shortcut.Save
