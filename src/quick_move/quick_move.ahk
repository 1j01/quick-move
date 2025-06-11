#Requires AutoHotkey v2.0

#HotIf WinActive("ahk_class CabinetWClass") or WinActive("ahk_class ExploreWClass")

^+x::  ; Ctrl+Shift+X
{
    ; Run("quick-move.exe") ; Closes immediately
    ; Run("quick-move.exe --from-clipboard") ; Closes immediately

    REPO_DIR := A_ScriptDir "\..\.."
    BIN_DIR := REPO_DIR "\.venv\Scripts"
    CLI := BIN_DIR "\quick-move.exe"
    ; Run('"' CLI '"') ; Runs, but with a console window behind it
    ; Run('"' CLI '"', , "Hide") ; Runs, but in the background (behind the explorer window)
    Run('"' CLI '" --from-clipboard', , "Hide") ; Runs, but in the background (behind the explorer window)
    ; DllCall("Shell32\ShellExecute", "ptr", 0, "str", "open", "str", '"' CLI '"', "str", "--from-clipboard", "str", "", "int", 0) ; Runs, but in the background (behind the explorer window)

    ; Run("C:\Users\Isaiah\AppData\Local\Programs\Python\Python313\Scripts\quick-move.exe --from-clipboard") ; Closes immediately
    ; Run("C:\Users\Isaiah\AppData\Local\Programs\Python\Python313\Scripts\quick-move.exe", , "Hide") ; Doesn't show up
    ; Run("C:\Users\Isaiah\AppData\Local\Programs\Python\Python313\Scripts\quick-move.exe")  ; Closes immediately

    ; REPO_DIR := A_ScriptDir "\..\.."
    ; BIN_DIR := REPO_DIR "\.venv\Scripts"
    ; PYTHON := BIN_DIR "\python.exe"
    ; ; Run('"' PYTHON '" -m quick_move') ; Runs, but with a console window behind it
    ; Run('"' PYTHON '" -m quick_move --from-clipboard', , "Hide") ; Runs, but in the background (behind the explorer window)

    A_TitleMatchMode := 3 ; Exact match
    ; WinActivate("Quick Move") ; Doesn't bring it to the front, just makes the taskbar button flash
    ; WinSetAlwaysOnTop(True, "Quick Move") ; Helps but sometimes errors saying the window is not found
    WinWait("Quick Move", , 5)
    WinSetAlwaysOnTop(True, "Quick Move")
    WinActivate("Quick Move")
}

#HotIf

;--------------------------------------------------------

; RunWaitOne(command) {
;     shell := ComObject("WScript.Shell")
;     ; Execute a single command via cmd.exe
;     exec := shell.Exec(A_ComSpec " /C " command)
;     ; Read and return the command's output
;     return exec.StdOut.ReadAll()
; }

; IsExplorerActive()
; {
;     try {
;         ; TODO: check for CabinetWClass? idk this seems to basically work
;         ; I haven't noticed it applying to the taskbar or anything so far,
;         ; though I know explorer.exe does more than just the file explorer
;         hwnd := WinActive("A")
;         pid := WinGetPID(hwnd)
;         return ProcessGetName(pid) = "explorer.exe"
;     }
;     catch {
;         return false
;     }
; }

;--------------------------------------------------------
; AUTO RELOAD THIS SCRIPT on Ctrl+S
;--------------------------------------------------------
~^s:: {  ; Ctrl+S (passive, allowing other applications to handle it too)
    if WinActive(A_ScriptName) {
        SplashGui := MakeSplash("AHK Auto-Reload", "`n  Reloading " A_ScriptName "  `n")
        Sleep(500)
        SplashGui.Destroy()
        Reload
    }
}

MakeSplash(Title, Text) {
    SplashGui := Gui(, Title)
    SplashGui.Opt("+AlwaysOnTop +Disabled -SysMenu +Owner")  ; +Owner avoids a taskbar button.
    SplashGui.Add("Text", , Text)
    SplashGui.Show("NoActivate")  ; NoActivate avoids deactivating the currently active window.
    return SplashGui
}
