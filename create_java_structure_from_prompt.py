from omni_automator.core.ai_task_executor import AITaskExecutor

prompt = "create a folder called java on Desktop and in tha fodler create 15 fodlers called java_1 and so on and in each of those java_1 to java_10 create folders called src and module and config module and also a text document along with those src and config and modules folder which contain text hi i am java_1 adn so on upto java_10 folders"

if __name__ == '__main__':
    executor = AITaskExecutor()
    res = executor.parse_and_execute_nl(prompt)
    print(res)
