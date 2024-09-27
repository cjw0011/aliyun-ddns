# aliyun-ddns
在具备动态公网IP出口的情况下通过修改阿里云DNS记录实现DDNS的功能 

------------------------------------------------------------------------------
1.此脚本希望通过简单的代码实现DNS记录的修改 
2.为了aliyun access-ID和access-secret的安全性，使用了环境变量的方式进行ID和secret的调用 
3.配置方式如下 
WINDOWS: 
1> 右键点击“此电脑”或“我的电脑”，选择“属性”。 
2> 点击“高级系统设置”。 
3> 在弹出的窗口中，点击“环境变量”按钮。 
4> 在“系统变量”或“用户变量”下，点击“新建”。 
5> 分别输入变量名 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET，以及它们的值。 
6> 点击“确定”保存设置。 
7> 重启PC 

 LINUX/MAC: 
nano ~/.bash_profile
export ALIBABA_CLOUD_ACCESS_KEY_ID="your_access_key_id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_access_key_secret"
source ~/.bash_profile
简简单单希望有帮助


