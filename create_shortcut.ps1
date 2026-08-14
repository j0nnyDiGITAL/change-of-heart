 = New-Object -ComObject WScript.Shell
 = .CreateShortcut("C:\Users\kufis\Desktop\P5R Save Editor.lnk")
.TargetPath = "E:\ai-workspace\knowledge-base\projects\p5r-save-editor\P5R_Save_Editor.vbs"
.WorkingDirectory = "E:\ai-workspace\knowledge-base\projects\p5r-save-editor"
.Description = "Persona 5 Royal Steam Save Editor"
.Save()
