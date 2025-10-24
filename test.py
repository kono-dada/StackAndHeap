from agent.utils import apply_patch
from agent.context import DEFAULT_note


test_patch = "*** Begin Patch\n@@ ## User Profile\n > this section is for storing user profile information, including factual information and your conjectures.\n \n -(empty for now)\n +last_user_reaction: \"短促且防备（\'你谁啊一上来就问这问那的\'，\'我跟你很熟吗\'），使用‘逆天’表达可能的认可或惊讶\"\n@@ ## Plan\n > this section is for storing your current plan, including subgoals, next steps, and any relevant context.\n \n -(empty for now)\n +继续在greet_and_probe frame中以低投入、短句的方式和用户互动，等待用户回应并在获得可用信息后把兴趣/偏好保存到User Profile。\n*** End Patch\n"

print(test_patch)
print()
print(apply_patch(test_patch, DEFAULT_note))