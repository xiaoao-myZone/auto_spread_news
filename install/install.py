import os,sys
exetend_list = ['jieba','numpy','pandas','Pillow','pywin32','requests','selenium==3.141.0','bs4','shutil']
current_dir = sys.path[0]

os.chdir(current_dir)
for i in exetend_list:
    #path = os.path.join(current_dir,i)
    #os.system(r'pip3 -m install %s' %i)
    f = os.popen(r'pip3 install %s' %i,'r')
    message = f.read()
    f.close()
    print(message)
    if 'Successfully installed' in message:
        continue
    else:
        print('%s安装出现异常' %i)
        input('回车继续\n')

# import shutil

