print("Welcome to MiniTask!")
tasks = []

while True:
    print("\nWhat would you like to do?")
    print("1. Add a task")
    print("2. View tasks")
    print("3. Mark a task as complete")
    print("4. Quit")

    choice = input("Enter your choice: ")

    if choice == "1":
        task = input("Enter a task: ")
        tasks.append({"name": task, "completed": False})
        print("Task added!")

    elif choice == "2":
        if len(tasks) == 0:
            print("You have no tasks.")
        else:
            print("\nYour tasks:")
            for i in range(len(tasks)):
                status = "✓" if tasks[i]["completed"] else " "
                print(str(i + 1) + ". [" + status + "] " + tasks[i]["name"])

    elif choice == "3":
        if len(tasks) == 0:
            print("You have no tasks to complete.")
        else:
            number = int(input("Enter the task number to complete: "))

            if number >= 1 and number <= len(tasks):
                tasks[number - 1]["completed"] = True
                print("Task completed!")
            else:
                print("Invalid task number.")

    elif choice == "4":
        print("Goodbye!")
        break

    else:
        print("Invalid choice. Please try again.")
