import functools, os, sys
import numpy as np
import tensorflow as tf
import tempfile
from PIL import Image
import matplotlib.pyplot as plt
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename

DATA_FOLDER = 'data'
PUBLIC_FOLDER = '../public'
QUERY_FOLDER = '/datax/query'
TMP_FOLDER = 'tmp'
SYS_TMP_FOLDER = tempfile.gettempdir()

STATIC_FOLDER = os.path.join('flaskr', 'static')

ALLOWED_EXTENSIONS = set(['npy'])
MAX_FILE_SIZE = 32 * 1024 * 1024

KEYS_PATH = os.path.join(QUERY_FOLDER, 'keys.npy')
META_PATH = os.path.join(QUERY_FOLDER, 'meta.npy')
MODEL_PATH = os.path.join(DATA_FOLDER, 'frozen_model.pb')

bp = Blueprint('core', __name__, url_prefix='/')

# load data
keys = np.load(KEYS_PATH)
meta = np.load(META_PATH)

def _load_graph(frozen_graph_filename):
   """ Function to load frozen TensorFlow graph"""
   with tf.gfile.GFile(frozen_graph_filename, "rb") as f:
       graph_def = tf.GraphDef()
       graph_def.ParseFromString(f.read())
   with tf.Graph().as_default() as graph:
       tf.import_graph_def(graph_def, name="prefix")
   return graph

def _plot_image(target_path, img, img_):
    f, ax = plt.subplots(2, 1, figsize=(8,5))
    ax[0].imshow(img.squeeze(), aspect='auto')
    ax[0].set_title("Your Input")
    ax[1].imshow(img_.squeeze(), aspect='auto')
    ax[1].set_title("Best Match")
    ax[1].set_ylabel("Time")
    plt.tight_layout()
    plt.savefig(target_path)
    return 

def _parse_meta(meta):
    basename = '_'.join(meta[0].split('.'))
    idx = meta[1]
    fields = basename.split('_')
    prefix = '_'.join(fields[:3])
    time_stamp = '_'.join(fields[3:5])
    obstarget = fields[5]
    scan_num = fields[6]
    coarse_chan = fields[9]
    return prefix, time_stamp, obstarget, scan_num, coarse_chan, idx

def _retrieve_image(meta, data_dir="/datax/theta3_split/"):
    prefix, time_stamp, obstarget, scan_num, coarse_chan, idx = _parse_meta(meta)
    path = data_dir+'/'.join([prefix, obstarget, time_stamp, scan_num, coarse_chan, idx])+'.npy'
    try:
        img_ = np.load(path).squeeze()
    except:
        print("Image path not exist", path)
        img_ = None
    return img_

graph = _load_graph(MODEL_PATH)
x = graph.get_tensor_by_name('prefix/input_:0')
y = graph.get_tensor_by_name('prefix/enc_norm:0')
sess = tf.Session(graph=graph)

num_dims = keys.shape[1]

def allowed_file(filename):
    # returns true if file's extension is supported
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=('GET', 'POST'))
def home():
    return render_template('core/home.html', wat_image=request.args.get('wat_image'))
    
@bp.route('/image/<path:filename>', methods=('GET',))
def serve_image(filename):
    if filename[:7] != 'bl-img-' or filename[-4:] != '.png':
        abort(403)
    return send_from_directory(SYS_TMP_FOLDER, filename)

@bp.route('/public/<path:filename>', methods=('GET',))
def serve_public(filename):
    return send_from_directory(PUBLIC_FOLDER, filename)

@bp.route('/query', methods=('POST',))
def query_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'message': 'No file specified'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No file specified'})

        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        if file_length > MAX_FILE_SIZE:
            return jsonify({'message': 'File exceeds size limit of ' + str(MAX_FILE_SIZE//1024//1024) + ' MB'})
        file.seek(0, os.SEEK_SET)
        if file and allowed_file(file.filename):
            try:
                # save the file
                filename = os.path.join(TMP_FOLDER, 'f' + next(tempfile._get_candidate_names()))
                file.save(filename)

                #try:
                im = np.load(filename).astype(np.float32)
                im *= (1.0/im.max())

                # check image size
                if im.shape != (16, 128):
                    print("Unsupported image dimensions received")
                    return jsonify({'message': 'unsupported image dimensions. Only 16x128 images allowed.'})
                im = im.reshape((1, 16, 128, 1)).astype(np.float32)

                # run tensorflow inference
                vec = sess.run(y, feed_dict={x: im})
                
                # compare with keys
                sim = keys @ vec.reshape((32,))
                idx = np.argmax(sim)
                
                im_ = _retrieve_image(meta[idx])
                if im_ is None:
                    im_ = np.ones_like(im)
                wat_path = 'bl-img-' + next(tempfile._get_candidate_names()) + '.png'
                im_ *= (1.0/im_.max())

                _plot_image(os.path.join(SYS_TMP_FOLDER, wat_path), im.squeeze(), im_.squeeze())

                prefix, time_stamp, obstarget, scan_num, coarse_chan, subidx = _parse_meta(meta[idx])

                f0 = 2802.83203125 #Sband
                foff =-2.7939677238464355e-6
                centerfreq = f0 + foff*(float(coarse_chan)*1024**2+float(subidx))
                obj = {
                    'prefix': prefix,
                    'target': obstarget,
                    'timestamp': time_stamp,
                    'scannum': scan_num,
                    "band": "S", 
                    'coarsechnl': coarse_chan,
                    'centerfreq': float(centerfreq), 
                    'idx': int(idx),
                    'dist': float(1.-sim[idx]),
                    'wat_path': '/image/' + wat_path
                }
                
                os.remove(filename)
                return jsonify(obj)
            except:
                return jsonify({'message': 'Unknown error'})
        else:
            return jsonify({'message': 'Unsupported format, only .npy allowed'})
