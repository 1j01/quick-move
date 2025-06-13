
## Ideas

There's a common type of reorganization that I add support for that wouldn't need AI but would feel pretty magical:
Moving mediaCategory/projectName into a projectName/mediaCategory folder  
e.g. "Screenshots/Tiamblia/Screenshot 23409234.png" -> "Project Stuff/Tiamblia/Screenshots/Screenshot 23409234.png"  
or "Screenshots/Tiamblia 23409234.png" -> "Project Stuff/Tiamblia/Screenshots/Tiamblia 23409234.png"  
or "Screenshots/Tiamblia" -> "Tiamblia/Screenshots" (suggest to rename the folder being moved)  
I could suggest creating this Screenshots folder based on a simple rule:  
if part of the path of the file being moved (all files being moved) matches part of the path of the destination, look at the next outer folder name; if it's not present in the destination search, tack it on the end  
something like that  

Could also suggest folders based on shared file types, e.g. for a selection of ".wav" and ".mp3" files, suggest a "Music" or "Audio" or "Sound" folder, or for a selection of ".png" and ".jpg" files, suggest an "Images" or "Pictures" folder. For arbitrary file extensions, suggest a folder named after the extension.

Could also suggest folders based on shared prefixes or parts of the file names, e.g. for a selection of "Tiamblia 23409234.png" and "Tiamblia 23409235.png", suggest a "Tiamblia" folder. Sometimes this ought to be pluralized, e.g. for "Screenshot 23409234.png" and "Screenshot 23409235.png", suggest a "Screenshots" folder.

Of course AI could cover these use cases, but it wouldn't be as reliable, and it would be slower.

Could look at fuzzy matching implementations in other software, like VS Code, as well as libraries like `fuzzywuzzy` or `rapidfuzz`.

Could maybe use `QtGui.QClipboard` instead of `pyperclip`. Aside from removing a dependency, it would allow targeting specific MIME types, like text/url-list which may be set by some file managers.
