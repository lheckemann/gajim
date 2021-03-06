rmdir /S /Q gajim_built

mkdir gajim_built
hg archive gajim_built
xcopy ..\gajim-plugins\plugin_installer gajim_built\plugins\plugin_installer /e /i

rem copy C:\Python34\Lib\site-packages\gnome\msgfmt.exe gajim_built
rem copy C:\Windows\System32\msvcr100.dll gajim_built

cd gajim_built

for %%l in (po\*.po) do mkdir po\%%~nl & mkdir po\%%~nl\LC_MESSAGES & msgfmt -o po\%%~nl\LC_MESSAGES\gajim.mo %%l

c:\python34\python.exe setup_win32.py build_exe

move build\exe.win32-3.4 .
rmdir build
rename exe.win32-3.4 build

rem REM for snarl plugin
rem xcopy ..\win32com build\win32com /e /i

"C:\Program Files (x86)\NSIS\makensis" gajim.nsi

cd ..