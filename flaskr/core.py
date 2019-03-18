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

MODEL_NAMES = [ "Conv Noise", "Fully Connected" ]
MODEL_PATHS = [
        os.path.join(DATA_FOLDER, 'conv_noise.pb'),
        os.path.join(DATA_FOLDER, 'frozen_model.pb')
        ]

KEY_PATHS = [
        os.path.join(QUERY_FOLDER, 'keys_conv_noise.npy'),
        os.path.join(QUERY_FOLDER, 'keys.npy')
        ]


META_PATH = os.path.join(QUERY_FOLDER, 'meta.npy')

bp = Blueprint('core', __name__, url_prefix='/')

# load data
keys = [np.load(path) for path in KEY_PATHS]
meta = np.load(META_PATH)

def _load_graph(frozen_graph_filename):
    """ Function to load frozen TensorFlow graph"""
    with tf.gfile.GFile(frozen_graph_filename, "rb") as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
    with tf.Graph().as_default() as graph:
        tf.import_graph_def(graph_def, name="prefix")
    return graph

def _plot_image(target_path, img, img_, f=None, ax=None):
    if f is None:
        f, ax = plt.subplots(2, 1, figsize=(8,5))
    ax[0].cla(); ax[1].cla()
    ax[0].imshow(img.squeeze(), aspect='auto')
    ax[0].set_title("Your Input")
    ax[1].imshow(img_.squeeze(), aspect='auto')
    ax[1].set_title("Best Match")
    ax[1].set_ylabel("Time")
    plt.tight_layout()
    plt.savefig(target_path)
    return f, ax

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

graphs = [_load_graph(path) for path in MODEL_PATHS]
x = [g.get_tensor_by_name('prefix/input_:0') for g in graphs]
y = [g.get_tensor_by_name('prefix/enc_norm:0') for g in graphs]
sess = [tf.Session(graph=g) for g in graphs]

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
        if 'num-results' not in request.form:
            return jsonify({'message': 'Number of results required'})
        if 'model-id' not in request.form:
            return jsonify({'message': 'Model ID required'})
        if 'file' not in request.files:
            return jsonify({'message': 'No file specified'})
        file = request.files['file']
        num_results = int(request.form.get('num-results'))
        model_id = int(request.form.get('model-id'))
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

                im = np.load(filename).astype(np.float32)
                im *= (1.0/im.max())

                # check image size
                if im.shape != (16, 128):
                    print("Unsupported image dimensions received")
                    return jsonify({'message': 'unsupported image dimensions. Only 16x128 images allowed.'})
                im = im.reshape((1, 16, 128, 1)).astype(np.float32)

                # run tensorflow inference
                vec = sess[model_id].run(y[model_id], feed_dict={x[model_id]: im})

                # compare with keys
                sim = keys[model_id] @ vec.reshape((32,))

                # find indices of best matches
                idxs = []
                if num_results == 1:
                    # fast-forward if only one match required
                    idxs = [np.argmax(sim)]
                else:
                    # else use quickselect partition
                    idxs = np.argpartition(-sim, np.arange(num_results))[:num_results]

                # create result set
                objs = []
                f_, ax_ = None, None
                for idx in idxs:
                    im_ = _retrieve_image(meta[idx])
                    if im_ is None:
                        im_ = np.ones_like(im)
                    wat_path = 'bl-img-' + next(tempfile._get_candidate_names()) + '.png'
                    im_ *= (1.0/im_.max())

                    f_, ax_ = _plot_image(os.path.join(SYS_TMP_FOLDER, wat_path), im.squeeze(), im_.squeeze(), f_, ax_)

                    prefix, time_stamp, obstarget, scan_num, coarse_chan, subidx = _parse_meta(meta[idx])

                    f0 = 2802.83203125 #Sband
                    foff =-2.7939677238464355e-6
                    centerfreq = f0 + foff*(float(coarse_chan)*1024**2+float(subidx))
                    dist = (2. * max(0., 1.-sim[idx])) ** 0.5
                    objs.append({
                        'prefix': prefix,
                        'target': obstarget,
                        'timestamp': time_stamp,
                        'scannum': scan_num,
                        "band": "S", 
                        'coarsechnl': coarse_chan,
                        'centerfreq': float(centerfreq), 
                        'idx': int(idx),
                        'dist': float(dist),
                        'wat_path': '/image/' + wat_path
                        });

                os.remove(filename)
                return jsonify({'message':'success', 'results': objs})
            except:
                return jsonify({'message': 'Unknown error'})
        else:
            return jsonify({'message': 'Unsupported format, only .npy allowed'})
