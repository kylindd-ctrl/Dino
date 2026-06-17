import os, sys, atexit
os.chdir(r'C:\Users\admin\Desktop\solar project\Release_v2_Step5')
sys.path.insert(0, '.')
try:
    from app import create_app
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
except Exception as e:
    import traceback
    with open('server_error.log', 'w') as f:
        f.write(traceback.format_exc())
    raise
