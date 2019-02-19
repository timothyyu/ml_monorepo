## Build nanomsg yourself

1. You need a c++ compilier installed. For instance visual c++.

2. Download [nanomsg source file](https://github.com/nanomsg/nanomsg); then copy its src folder to c:\anaconda3\inlude\ and change the folder name from src to nanomsg

3. Copy EliteQuant_Python\source\server\nanomsg.lib to c:\anaconda3\libs; or build one from the c source code

4. Download [nanomsg python](https://github.com/tonysimpson/nanomsg-python), then execute the following

```
cd nanomsg-python
python setup.py build_ext
python setup.py install
```

This should install nanomsg to C:\Anaconda3\Lib\site-packages\nanomsg-1.0-py3.6-win-amd64.egg\

5. Copy nanomsg.dll to C:\Anaconda3\Lib\site-packages\nanomsg-1.0-py3.6-win-amd64.egg\