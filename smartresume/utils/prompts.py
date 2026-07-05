"""
Prompt management module
"""
from typing import Dict

SYSTEM_PROMPT = """
You are a professional resume parsing assistant. Parse the given resume text into structured JSON.
For bilingual resumes (Chinese+English), prioritize the Chinese content. For English-only resumes, extract English content.
您是专业的简历解析助手，将简历文本转换为结构化JSON。中英文混合简历优先中文内容。
"""

UNIFIED_PROMPT = """
Read the ENTIRE resume text carefully. Extract ALL information you can find into the JSON structure below.
IMPORTANT: Do NOT rely on exact section titles. The resume may use different headings like "工作经历", "工作经验", "实习经历",
"项目经历", "项目经验", "研究经历", "科研经历", "Work Experience", "Projects", "Research", "Internship", etc.
Identify sections by their CONTENT, not their titles. If a section describes work done at a company → it's work experience.
If it describes a project → it's a project. If it describes academic research → it's research.

仔细阅读整份简历，提取你能找到的所有信息。不要依赖精确的栏目标题——通过内容判断类型。
在公司做的事情→工作经历；课题/项目→项目经历；学术研究→研究经历。

Output JSON:
{
  "basicInfo": {
    "name": "",              // 姓名 Name
    "personalEmail": "",     // 邮箱 Email
    "phoneNumber": "",       // 电话 Phone (keep original format 保留原文格式含国家码)
    "age": "",              // 年龄 Age
    "born": "",             // 出生年月 Birth year-month 如 1996-11
    "gender": "",           // 性别 Gender
    "desiredLocation": [],  // 期望工作城市 Desired cities 如 ["北京"]，不存在则[]
    "currentLocation": "",  // 现居地 Current city
    "placeOfOrigin": "",    // 籍贯 Hometown
    "summary": ""           // 个人总结/求职意向 Self-introduction or career objective
  },
  "education": [{
    "degreeLevel": "",      // 学位 Degree：本科/硕士/博士/专科/高中 Bachelor/Master/PhD
    "school": "",           // 学校 School
    "major": "",            // 专业 Major
    "department": "",       // 系/学院 Department
    "period": { "startDate": "", "endDate": "" },  // yyyy 或 yyyy.mm，在读填"至今"/"present"
    "gpa": "",              // GPA if available
    "educationDescription": "" // 教育描述：课程、荣誉、论文等 Education details
  }],
  "experiences": [{         // ALL experiences combined - work, internship, project, research
                            // 所有经历统一放这里：工作、实习、项目、研究
    "type": "",             // "work" / "internship" / "project" / "research"
                            // 工作/实习/项目/研究 — judge by content, not section title
    "title": "",            // 经历标题：职位名称 或 项目名称 Position or project name
    "organization": "",     // 组织名称：公司名 或 学校/实验室名 Company or institution
    "role": "",             // 角色：高级工程师/开发人员/第一作者/项目负责人
    "period": { "startDate": "", "endDate": "" },
    "description": "",      // 详细描述：职责、技术栈、成果、论文发表等 Description, tech stack, achievements
    "skills": []            // 这段经历涉及的技术/技能 Technologies used in this experience
  }],
  "skills": [],             // 整体技能列表 Overall skill list
  "certifications": [{      // 证书/资质/获奖 Certificates, awards, honors
    "name": "",
    "date": "",
    "description": ""
  }]
}

Rules / 规则:
1. Extract ALL experiences — work, internships, projects, research — into the "experiences" array. Do NOT skip any.
   将所有经历（工作、实习、项目、研究）都提取到 experiences 数组中，不要遗漏。
2. Classify each experience by its CONTENT. If someone led a team at Alibaba → type:"work".
   If someone did an academic paper → type:"research". If someone built a system for coursework → type:"project".
   通过内容判断类型，不是通过栏目标题。
3. Use empty string "" for missing fields, empty array [] for missing lists.
   不存在的字段填空字符串""，不存在的列表填[]。
4. Be precise — extract dates, numbers, and technical terms exactly as written.
   精确提取日期、数字、技术术语。
"""


def get_prompts() -> Dict[str, str]:
    """Get all prompts - now using unified extraction"""
    return {
        "unified": SYSTEM_PROMPT + UNIFIED_PROMPT,
    }
