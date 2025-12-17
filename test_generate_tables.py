from omni_automator.core.ai_task_executor import AITaskExecutor

if __name__ == '__main__':
    executor = AITaskExecutor()
    res = executor._handle_generate_code(module_name='xyz', create_multiplication_tables=True, start=1, end=20, table_size=10)
    print(res)
