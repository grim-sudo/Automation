from omni_automator.core.ai_task_executor import AITaskExecutor
import os

if __name__ == '__main__':
    executor = AITaskExecutor()
    desktop = os.path.expanduser('~/Desktop')

    # Create main folder
    main = executor._handle_create_folder(name='python', location=desktop)
    if not main.get('success'):
        print({'success': False, 'error': 'Failed to create main folder', 'details': main})
        raise SystemExit(1)

    main_path = main['path']

    # Create python_1 .. python_10
    bulk = executor._handle_create_bulk_folders(base_path=main_path, folder_prefix='python_', start=1, end=10)
    created = [main_path]
    if bulk.get('success'):
        created.extend(bulk.get('created_folders', []))

    # In each created folder, create src, module, config
    created_sub = []
    for folder in bulk.get('created_folders', []):
        for sub in ['src', 'module', 'config']:
            res = executor._handle_create_folder(name=sub, location=folder)
            if res.get('success'):
                created_sub.append(res['path'])

    summary = {
        'success': True,
        'main_folder': main_path,
        'created_count': len(created) + len(created_sub),
        'created_paths': created + created_sub
    }

    print(summary)
