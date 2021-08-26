import os
import math
import subprocess

#TODO: could decrease the amount of subprocess calls now that it is being done at creation and 
#Stored in DB
# add: dur(seconds), dim(w,h)
def capture(full_path, milli):
    filename=full_path.split('/')[len(full_path.split('/'))-1]
    o_h = 150
    dur = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration','-of', 'default=noprint_wrappers=1:nokey=1',full_path])
    dur_f = float(dur.decode('ascii').rstrip())
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', full_path])
    out = out.decode('ascii').rstrip()
    dem = out.split('x')
    hidden = '{0}.{1}/'.format(full_path[:full_path.index(filename)], filename[:filename.index('.mp4')])
    if '.{0}'.format(filename[:filename.index('.mp4')]) not in os.listdir(full_path[:full_path.index(filename)]):
        subprocess.Popen(['mkdir', hidden])
    time = convert_secs(milli)
    name = '{0}{1}.png'.format('img_',str(milli))
    cmd = ['ffmpeg', '-ss',time,'-i', full_path, '-vframes', '1', '-s', str(round(((int(dem[0])/int(dem[1])*o_h)))) + 'x' + str(o_h),name]
    proc = subprocess.Popen(cmd)
    proc.wait()
    subprocess.Popen(['mv',name,hidden])
    return hidden + name

def convert_secs(secs):
    hours = math.floor((secs/(60*60))%24)
    minu = math.floor((secs/60)%60)
    seconds = secs%60
    result = "{0:02}:{1:02}:{2:06.3f}".format(hours,minu,seconds)
    if secs == 0:
        return "00:00:02.000"
    else:
        return result