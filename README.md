# Solution

Before running the solution, eFLINT Server has to be instantiated within a Docker Container.
Steps:
1. Ensure that Docker Desktop is installed on your system.
2. Make sure that the Docker Daemon is running (i.e. Docker Desktop is started).
3. Run  ```docker-compose up``` from the solution's root folder.

Congratulations! You now have eFLINT Server running on a Docker Container, exposed locally on port 8080.

To make use of the Python solution, we recommend that you open the root folder as a project within any IDE supporting Python (for example, PyCharm).
The project's main entry point is ```executor.py```. Make sure to run the project from this main file.

```executor.py``` contains two relative paths, ```plans_path``` and ```policies_path```. These should be amended according to which collection of plans and policies you would like to simulate from the solution. For example:

```
plans_path = "./case-studies/case-study-1-plans"
policies_path = './case-studies/case-study-1-policies/policies.eflint'
```

NOTE: The manner in which the eFLINT server is set up allows only **3** eFLINT instances to run concurrently. If this number of instances is exceeded, without terminating the active instances, requests to the eFLINT reasoner may not be handled successfully. Make sure that no more than 3 instances are running concurrently. If direct termination of individual instances is not possible, we suggest restarting the docker container.
