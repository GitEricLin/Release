# -*- coding: utf-8 -*-
"""Untitled3.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Wojcx-ZEcUchR7mSQYdJz-bYXwrEVAzV
"""

# install package
!pip install pandas tqdm sklearn xgboost matplotlib numpy scipy shap lime

import pandas as pd
import os
from tqdm import tqdm
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn import metrics
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import numpy as np
import scipy
from sklearn.model_selection import StratifiedKFold
import shap as sp
import lime as lm
from sklearn.calibration import calibration_curve
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV

def main():
    pd.options.mode.chained_assignment=None
    path = 'Dataset.csv'
    param = []
    if 'Weaning' in path:
        param = [421/539, 770, 3, 5]
    elif 'Mortality' in path:
        param = [783/179, 3850, 4, 6]
    x,y=InputData(path) # 讀取檔案、計算mean及std
    xgbm=xgb.XGBClassifier(scale_pos_weight=param[0], #M:783/179, W:421/539
                           learning_rate=0.01,
                           n_estimators=param[1], #M:3850 W:770
                           gamma=0,
                           max_depth=param[2], #M:4 W:3
                           min_child_weight=param[3], #M:6 W:5
                           subsample=1,
                           eval_metric='error')
    rfm=RandomForestClassifier(n_estimators=100,max_depth=4)
    lrm=LogisticRegression(solver='saga',max_iter=10000)

    # print params
    print(xgbm.get_params())
    print(rfm.get_params())
    print(lrm.get_params())
    
    #gridsearch(x,y)
    ExperimentI(x,y,xgbm,rfm,lrm) # AUROC
    ExperimentII(x,y,xgbm,rfm,lrm) # delong Test and 95% CI
    ExperimentIII(x,y,xgbm,rfm,lrm) # 產生 Predict, recall, f1score, brier score 等
    ExperimentIV(x,y,xgbm,rfm,lrm) # SHAP value 及 Feature Importance
    ExperimentV(x,y,xgbm,rfm,lrm) # LIME

def InputData(path):
    dataset=pd.read_csv(path)
    dataset_alive=pd.read_csv(path)
    dataset_dead=pd.read_csv(path)
    """
    print('Datasize: %d x %d'%(len(dataset.index),len(dataset.columns)))
    count=0
    for i in range(2,len(dataset.columns)):
        for j in range(0,len(dataset.index)):
            if pd.isna(dataset[dataset.columns[i]][j]):
                if count is 0:
                    print(dataset.columns[i],end=': ')
                count+=1
        if count is not 0:
            print(count)
            count=0
    """
    try:
        # 刪除空行並統計總人數、活著及死亡人數
        dataset[dataset.columns[1]]=dataset[dataset.columns[1]].fillna("2")
        #dataset = dataset.replace({'Sex':{'M': 1, 'F': 2}})
        #dataset['Sex']=dataset['Sex'].fillna(dataset['Sex'].mean())
        for i in range(len(dataset)-1,-1,-1):
            if dataset[dataset.columns[1]][i] == "2": #把空行刪掉
                dataset = dataset.drop(dataset.index[i])
        dataset_alive = dataset
        for i in range(len(dataset_alive)-1, -1, -1):
            if dataset_alive[dataset_alive.columns[1]][i] == 1 or dataset_alive[dataset_alive.columns[1]][i] == '1': #只留下=0 Mortality=0
                dataset_alive = dataset_alive.drop(dataset_alive.index[i])
        dataset_dead = dataset
        for i in range(len(dataset_dead)-1,-1,-1):
            if dataset_dead[dataset_dead.columns[1]][i] == 0 or dataset_dead[dataset_dead.columns[1]][i] == '0': #只留下=1 Mortality=1
                dataset_dead = dataset_dead.drop(dataset_dead.index[i])

        dataset[dataset.columns[1]] = dataset[dataset.columns[1]].astype(float)

        total_avg = []
        alive_avg = []
        dead_avg = []
        p_value = []
        # 產生 Table1
        with tqdm(range(2,len(dataset.columns))) as bar:
            ftName=[]
            for i in bar:
                dataset[dataset.columns[i]]=dataset[dataset.columns[i]].fillna(str(dataset[dataset.columns[i]].mean()))
                dataset[dataset.columns[i]] = dataset[dataset.columns[i]].astype(float)
                ftName.append(dataset.columns[i])
                pvalue_temp = t_test(dataset_alive[dataset_alive.columns[i]], dataset_dead[dataset_dead.columns[i]])[1]
                #print(i, pvalue_temp)
                if pvalue_temp < 0.01 and pvalue_temp != 0: p_value.append("< 0.01")
                elif np.isnan(pvalue_temp): p_value.append("0")
                else: p_value.append('%.2f'%pvalue_temp)

                if dataset.columns[i] in ["Carbapenem W01", "Carbapenem W02", "Carbapenem W03", "Carbapenem W04", "Carbapenem W05", "Carbapenem W06", "Carbapenem W07",
               "Carbapenem W08", "Carbapenem W09", "Colistin W01", "Colistin W02", "Colistin W03", "Colistin W04", "Colistin W05",
               "Colistin W06", "Colistin W07", "Colistin W08", "Colistin W09", "Anti_fungal W01", "Anti_fungal W02", "Anti_fungal W03",
               "Anti_fungal W04", "Anti_fungal W05", "Anti_fungal W06", "Anti_fungal W07", "Anti_fungal W08", "Anti_fungal W09",
               "Anti_CMV W01", "Anti_CMV W02", "Anti_CMV W03", "Anti_CMV W04", "Anti_CMV W05", "Anti_CMV W06", "Anti_CMV W07", "Anti_CMV W08",
               "Anti_CMV W09", "Anti_MRSA W01", "Anti_MRSA W02", "Anti_MRSA W03", "Anti_MRSA W04", "Anti_MRSA W05", "Anti_MRSA W06",
               "Anti_MRSA W07", "Anti_MRSA W08", "Anti_MRSA W09", "Vasopressor W01", "Vasopressor W02", "Vasopressor W03", "Vasopressor W04", "Vasopressor W05",
               "Vasopressor W06", "Vasopressor W07", "Vasopressor W08", "Vasopressor W09","DNR", "Weaning", "Mortality", "Sex", "Summary Hospice", "Summary Diagnosis", "HTN", "DM", "CVA/dementia", "CHF", "Af", "COPD", "Asthma", "Summary Gastrointestinal_bleeding", "Summary Cirrhosis", "Summary ERSD", "NewHD", "Summary Active_Cancer", "Summary Cancer_history", "Summary Autoimmunity", "Summary Organ_transplantation"]:
                    # 算 % 數
                    temp_count_total = 0
                    temp_count_alive = 0
                    temp_count_dead = 0
                    #print(dataset.columns[i])
                    for j in range(0,len(dataset[dataset.columns[i]])):
                        if int(dataset[dataset.columns[i]][j]) == 1:
                          temp_count_total += 1
                    for j in range(0,len(dataset_alive[dataset_alive.columns[i]])):
                        #print(dataset_alive[dataset_alive.columns[i]])
                        try:
                          if int(dataset_alive[dataset_alive.columns[i]][j]) == 1:
                            temp_count_alive += 1
                          else:
                            #print(j, dataset_alive[dataset_alive.columns[i]][j])
                            pass
                        except:
                          pass
                    for j in range(0,len(dataset_dead[dataset_dead.columns[i]])):
                        try:
                          if int(dataset_dead[dataset_dead.columns[i]][j]) == 1:
                            temp_count_dead += 1
                        except:
                          pass
                    
                    total_avg.append(str(sum(dataset[dataset.columns[i]])) + '(' + '%.1f'%(sum(dataset[dataset.columns[i]])/len(dataset[dataset.columns[i]])*100) + '%)')
                    alive_avg.append(str(sum(dataset_alive[dataset_alive.columns[i]])) + '(' + '%.1f'%(sum(dataset_alive[dataset_alive.columns[i]])/len(dataset_alive[dataset_alive.columns[i]])*100) + '%)')
                    dead_avg.append(str(sum(dataset_dead[dataset_dead.columns[i]])) + '(' + '%.1f'%(sum(dataset_dead[dataset_dead.columns[i]])/len(dataset_dead[dataset_dead.columns[i]])*100) + '%)')

                else:
                    if "FiO2" in dataset.columns[i]:
                        total_avg.append('%.4f'%(dataset[dataset.columns[i]].mean()) + '+ -' + '%.4f'%(dataset[dataset.columns[i]].std()))
                        alive_avg.append('%.4f'%(dataset_alive[dataset_alive.columns[i]].mean()) + '+ -' +  '%.4f'%(dataset_alive[dataset_alive.columns[i]].std()))
                        dead_avg.append('%.4f'%(dataset_dead[dataset_dead.columns[i]].mean()) + '+ -' + '%.4f'%(dataset_dead[dataset_dead.columns[i]].std()))
                    else:
                        total_avg.append('%.1f'%(dataset[dataset.columns[i]].mean()) + '+ -' + '%.1f'%(dataset[dataset.columns[i]].std()))
                        alive_avg.append('%.1f'%(dataset_alive[dataset_alive.columns[i]].mean()) + '+ -' +  '%.1f'%(dataset_alive[dataset_alive.columns[i]].std()))
                        dead_avg.append('%.1f'%(dataset_dead[dataset_dead.columns[i]].mean()) + '+ -' + '%.1f'%(dataset_dead[dataset_dead.columns[i]].std()))
    except KeyboardInterrupt:
        bar.close()
        raise
    bar.close()
    #dataset.to_csv(os.getcwd()+'//Dataset without missdata.csv',index=False)
    x=dataset[ftName]
    y=dataset[dataset.columns[1]]

    table1 = pd.DataFrame([ftName, total_avg, alive_avg, dead_avg, p_value]).T
    table1.columns = ['column_name', 'Total n=' + str(len(dataset[dataset.columns[i]])), 'Alive n=' + str(len(dataset_alive[dataset_alive.columns[i]])), 'Dead n=' + str(len(dataset_dead[dataset_dead.columns[i]])), 'P Value']
    table1.to_csv('Average_Weaning.csv', index=False) #_Mortality
    return x,y

def ExperimentI(x,y,xgbm,rfm,lrm): #AUC
    plt.rc('font', size=12)          # controls default text sizes
    plt.rc('axes', titlesize=12)     # fontsize of the axes title
    plt.rc('axes', labelsize=12)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=12)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=12)    # fontsize of the tick labels
    plt.rc('legend', fontsize=12)    # legend fontsize
    plt.rc('figure', titlesize=12)  # fontsize of the figure title
    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2,random_state=0)
    fig,ax=plt.subplots(1,1,figsize=(10,10))
    xgbm=xgbm.fit(x_train,y_train)
    y_pred=xgbm.predict_proba(x_test)[:,1]
    fpr,tpr,threshold=metrics.roc_curve(y_test,y_pred)
    roc_auc=metrics.auc(fpr,tpr)
    plt.plot(fpr,tpr,'r',label='XGBoost (AUC:%0.3F)'%roc_auc,linewidth=5,linestyle='-')
    rfm=rfm.fit(x_train,y_train)
    y_pred=rfm.predict_proba(x_test)[:,1]
    fpr,tpr,threshold=metrics.roc_curve(y_test,y_pred)
    roc_auc=metrics.auc(fpr,tpr)
    plt.plot(fpr,tpr,'b',label='RandomForest (AUC:%0.3F)'%roc_auc,linewidth=5,linestyle='-.')
    lrm=lrm.fit(x_train,y_train)
    y_pred=lrm.predict_proba(x_test)[:,1]
    fpr,tpr,threshold=metrics.roc_curve(y_test,y_pred)
    roc_auc=metrics.auc(fpr,tpr)
    plt.plot(fpr,tpr,'G',label='LogisticRegression (AUC:%0.3F)'%roc_auc,linewidth=5,linestyle=':')
    plt.legend(loc='lower right',frameon=False)
    plt.show()
    plt.savefig('AUROC.png')

def gridsearch(x,y):
    '''
    xgbm=xgb.XGBClassifier(scale_pos_weight=421/543, #M:787/179 W:421/539
                           learning_rate=0.007,
                           n_estimators=100, #100
                           gamma=0,
                           max_depth=4, #4
                           min_child_weight=2, #2
                           subsample=1,
                           eval_metric='error')
    '''
    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2,random_state=0)

    cv_params = {'n_estimators': [750, 770, 790, 810, 830]}
    other_params = {'scale_pos_weight': 421/539, 'learning_rate': 0.007, 'n_estimators': 770, 'max_depth': 3, 'min_child_weight': 5, 'seed': 0,
                    'subsample': 1, 'colsample_bytree': 1, 'gamma': 0}

    model = xgb.XGBRegressor(**other_params)
    optimized_GBM = GridSearchCV(estimator=model, param_grid=cv_params, scoring='r2', cv=5, verbose=1, n_jobs=4)
    optimized_GBM.fit(x_train, y_train)
    evalute_result = optimized_GBM.cv_results_
    print('每輪執行結果:{0}'.format(evalute_result))
    print('參數的最佳取值：{0}'.format(optimized_GBM.best_params_))
    print('最佳模型得分:{0}'.format(optimized_GBM.best_score_))
    """
    xgbm=xgbm.fit(x_train,y_train)
    y_pred=xgbm.predict_proba(x_test)[:,1]
    fpr,tpr,threshold=metrics.roc_curve(y_test,y_pred)
    roc_auc=metrics.auc(fpr,tpr)
    print(roc_auc)
    """
def ExperimentII(x,y,xgbm,rfm,lrm): #delong Test and 95% CI
    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2,random_state=0)
    xgbm=xgbm.fit(x_train,y_train)
    y_pred=xgbm.predict_proba(x_test)[:,1]
    y_pred_XGB=np.array(y_pred)
    rfm=rfm.fit(x_train,y_train)
    y_pred=rfm.predict_proba(x_test)[:,1]
    y_pred_RF=np.array(y_pred)
    lrm=lrm.fit(x_train,y_train)
    y_pred=lrm.predict_proba(x_test)[:,1]
    y_pred_LR=np.array(y_pred)
    y_ans=np.array(y_test)

    delong(y_ans,y_pred_XGB,y_pred_RF)
    delong(y_ans,y_pred_XGB,y_pred_LR)
    print('XGB: ',get_ci_auc(y_ans, y_pred_XGB))
    print('RF: ',get_ci_auc(y_ans, y_pred_RF))
    print('LR: ',get_ci_auc(y_ans, y_pred_LR))
    
def ExperimentIII(x,y,xgbm,rfm,lrm): #產生 Predict, recall, f1score等
    kfold=StratifiedKFold(n_splits=5)
    AS=[[],[],[]]
    BS=[[],[],[]]
    for train,test in kfold.split(x,y):
        x_train=x.drop(index=test)
        x_test=x.drop(index=train)
        y_train=y.drop(index=test)
        y_test=y.drop(index=train)
        y_ans=np.array(y_test)
        xgbm=xgbm.fit(x_train,y_train)
        y_pred=xgbm.predict(x_test)
        y_prob=xgbm.predict_proba(x_test)[:,1]
        AS[0].append('%.4f'%metrics.accuracy_score(y_ans,y_pred))
        BS[0].append('%.4f'%metrics.brier_score_loss(y_ans,y_prob))
        rfm=rfm.fit(x_train,y_train)
        y_pred=rfm.predict(x_test)
        y_prob=rfm.predict_proba(x_test)[:,1]
        AS[1].append('%.4f'%metrics.accuracy_score(y_ans,y_pred))
        BS[1].append('%.4f'%metrics.brier_score_loss(y_ans,y_prob))
        lrm=lrm.fit(x_train,y_train)
        y_pred=lrm.predict(x_test)
        y_prob=lrm.predict_proba(x_test)[:,1]
        AS[2].append('%.4f'%metrics.accuracy_score(y_ans,y_pred))
        BS[2].append('%.4f'%metrics.brier_score_loss(y_ans,y_prob))
    for i in range(0,3):
        for j in range(0,5):
            AS[i][j]=float(AS[i][j])
            BS[i][j]=float(BS[i][j])
    print('Accuracy brier_score')
    for i in range(0,3):
        print('%.2f, %.2f'%(max(AS[i])*100,min(BS[i])*100))
    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2,random_state=0)
    y_ans=np.array(y_test)
    xgbm=xgbm.fit(x_train,y_train)
    y_pred=xgbm.predict(x_test)
    print(metrics.classification_report(y_ans,y_pred))
    rfm=rfm.fit(x_train,y_train)
    y_pred=rfm.predict(x_test)
    print(metrics.classification_report(y_ans,y_pred))
    lrm=lrm.fit(x_train,y_train)
    y_pred=lrm.predict(x_test)
    print(metrics.classification_report(y_ans,y_pred))

def ExperimentIV(x,y,xgbm,rfm,lrm): #SHAP 及 Feature Importance
    plt.rc('font', size=20)          # controls default text sizes
    plt.rc('axes', titlesize=20)     # fontsize of the axes title
    plt.rc('axes', labelsize=20)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=20)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=20)    # fontsize of the tick labels
    plt.rc('legend', fontsize=20)    # legend fontsize
    plt.rc('figure', titlesize=20)  # fontsize of the figure title
    
    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2,random_state=0)
    fig,ax=plt.subplots(1,1,figsize=(10,10))
    xgbm=xgbm.fit(x_train,y_train)
    explainer=sp.TreeExplainer(xgbm,feature_perturbation="tree_path_dependent")
    shap_values=explainer.shap_values(x_test)
    sp.summary_plot(shap_values,x_test) #, plot_type="bar",max_display=len(x_test)
    plt.show()
    plt.savefig('SHAP.png')
    print(shap_values)
    print(x_test)

    #ref: https://www.kaggle.com/wrosinski/shap-feature-importance-with-feature-engineering
    
    shap_sum = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame([x_test.columns.tolist(), shap_sum.tolist()]).T
    importance_df.columns = ['column_name', 'shap_importance']
    val = [[],[],[],[],[],[]]

    val[1] = list(importance_df['shap_importance'][0:4]) + list(importance_df['shap_importance'][19:66]) + list(importance_df['shap_importance'][138:192])
    val[2] = list(importance_df['shap_importance'][66:84]) + list(importance_df['shap_importance'][93:129])
    val[3] = list(importance_df['shap_importance'][246:]) + list(importance_df['shap_importance'][84:93]) + list(importance_df['shap_importance'][129:138])
    val[4] = list(importance_df['shap_importance'][192:246])
    val[5] = list(importance_df['shap_importance'][4:19])

    xgbmFI = xgbm.feature_importances_
    val[1] = list(xgbmFI[0:4]) + list(xgbmFI[19:66]) + list(xgbmFI[138:192])
    val[2] = list(xgbmFI[66:84]) + list(xgbmFI[93:129])
    val[3] = list(xgbmFI[246:]) + list(xgbmFI[84:93]) + list(xgbmFI[129:138])
    val[4] = list(xgbmFI[192:246])
    val[5] = list(xgbmFI[4:19])

    for i in range(1,6):
      print('#', 'Domain'+str(i), sum(val[i]))
    importance_df = importance_df.sort_values('shap_importance', ascending=False)
    for i in range(300):
      print(i, importance_df['column_name'][i], xgbmFI[i])#importance_df['shap_importance'][i]

    domain = [[],[],[],[],[],[]]
    # 其他 + 輸液灌食 + 特殊藥物
    domain[1] = ["DNR", "Sex", "BMI", "Summary Diagnosis", "ICU APACHEII Total Score", "RCC APACHEII Total Score",
          "Input W01", "Input W02", "Input W03", "Input W04", "Input W05", "Input W06", "Input W07", "Input W08", "Input W09",
          "Output W01", "Output W02", "Output W03", "Output W04", "Output W05", "Output W06", "Output W07", "Output W08", "Output W09",
          "Fluid balance W01", "Fluid balance W02", "Fluid balance W03", "Fluid balance W04", "Fluid balance W05", "Fluid balance W06",
          "Fluid balance W07", "Fluid balance W08", "Fluid balance W09", "Feeding amount W01", "Feeding amount W02", "Feeding amount W03",
          "Feeding amount W04", "Feeding amount W05", "Feeding amount W06", "Feeding amount W07", "Feeding amount W08", "Feeding amount W09",
          "Urine & HD output W01", "Urine & HD output W02",
          "Urine & HD output W03", "Urine & HD output W04", "Urine & HD output W05", "Urine & HD output W06",
          "Urine & HD output W07", "Urine & HD output W08", "Urine & HD output W09",
          "Carbapenem W01", "Carbapenem W02", "Carbapenem W03", "Carbapenem W04", "Carbapenem W05", "Carbapenem W06", "Carbapenem W07",
               "Carbapenem W08", "Carbapenem W09", "Colistin W01", "Colistin W02", "Colistin W03", "Colistin W04", "Colistin W05",
               "Colistin W06", "Colistin W07", "Colistin W08", "Colistin W09", "Anti_fungal W01", "Anti_fungal W02", "Anti_fungal W03",
               "Anti_fungal W04", "Anti_fungal W05", "Anti_fungal W06", "Anti_fungal W07", "Anti_fungal W08", "Anti_fungal W09",
               "Anti_CMV W01", "Anti_CMV W02", "Anti_CMV W03", "Anti_CMV W04", "Anti_CMV W05", "Anti_CMV W06", "Anti_CMV W07", "Anti_CMV W08",
               "Anti_CMV W09", "Anti_MRSA W01", "Anti_MRSA W02", "Anti_MRSA W03", "Anti_MRSA W04", "Anti_MRSA W05", "Anti_MRSA W06",
               "Anti_MRSA W07", "Anti_MRSA W08", "Anti_MRSA W09", "Vasopressor W01", "Vasopressor W02", "Vasopressor W03", "Vasopressor W04", "Vasopressor W05",
               "Vasopressor W06", "Vasopressor W07", "Vasopressor W08", "Vasopressor W09"]
    # 生理參數
    domain[2] = ["BT W01", "BT W02", "BT W03", "BT W04", "BT W05", "BT W06", "BT W07", "BT W08", "BT W09", "HR W01", "HR W02", "HR W03",
               "HR W04", "HR W05", "HR W06", "HR W07", "HR W08", "HR W09", "sysBP W01", "sysBP W02", "sysBP W03", "sysBP W04",
               "sysBP W05", "sysBP W06", "sysBP W07", "sysBP W08", "sysBP W09", "diaBP W01", "diaBP W02", "diaBP W03", "diaBP W04",
               "diaBP W05", "diaBP W06", "diaBP W07", "diaBP W08", "diaBP W09", "pulse pressure W01", "pulse pressure W02",
               "pulse pressure W03", "pulse pressure W04", "pulse pressure W05", "pulse pressure W06", "pulse pressure W07",
               "pulse pressure W08", "pulse pressure W09", "glucose W01", "glucose W02", "glucose W03", "glucose W04", "glucose W05",
               "glucose W06", "glucose W07", "glucose W08", "glucose W09"]
    # 呼吸照護
    domain[3] = ["FiO2 W01", "FiO2 W02", "FiO2 W03", "FiO2 W04", "FiO2 W05", "FiO2 W06", "FiO2 W07", "FiO2 W08", "FiO2 W09",
               "PEEP W01", "PEEP W02", "PEEP W03", "PEEP W04", "PEEP W05", "PEEP W06", "PEEP W07", "PEEP W08", "PEEP W09",
               "VTexp W01", "VTexp W02", "VTexp W03", "VTexp W04", "VTexp W05", "VTexp W06", "VTexp W07", "VTexp W08", "VTexp W09",
               "Minute ventilation W01", "Minute ventilation W02", "Minute ventilation W03", "Minute ventilation W04", "Minute ventilation W05",
               "Minute ventilation W06", "Minute ventilation W07", "Minute ventilation W08", "Minute ventilation W09",
               "PIP W01", "PIP W02", "PIP W03", "PIP W04", "PIP W05", "PIP W06", "PIP W07", "PIP W08", "PIP W09",
               "MAP W01", "MAP W02", "MAP W03", "MAP W04", "MAP W05", "MAP W06", "MAP W07", "MAP W08", "MAP W09",
               "RR W01", "RR W02", "RR W03", "RR W04", "RR W05", "RR W06", "RR W07", "RR W08", "RR W09",
               "SpO2 W01", "SpO2 W02", "SpO2 W03", "SpO2 W04", "SpO2 W05", "SpO2 W06", "SpO2 W07", "SpO2 W08", "SpO2 W09"]
    # 檢驗檢查
    domain[4] = ["ALB W01", "ALB W02", "ALB W03", "ALB W04", "ALB W05", "ALB W06", "ALB W07", "ALB W08", "ALB W09",
               "BIL.T W01", "BIL.T W02", "BIL.T W03", "BIL.T W04", "BIL.T W05", "BIL.T W06", "BIL.T W07", "BIL.T W08", "BIL.T W09",
               "ALT W01", "ALT W02", "ALT W03", "ALT W04", "ALT W05", "ALT W06", "ALT W07", "ALT W08", "ALT W09",
               "WBC W01", "WBC W02", "WBC W03", "WBC W04", "WBC W05", "WBC W06", "WBC W07", "WBC W08", "WBC W09",
               "HGB W01", "HGB W02", "HGB W03", "HGB W04", "HGB W05", "HGB W06", "HGB W07", "HGB W08", "HGB W09",
               "PLT W01", "PLT W02", "PLT W03", "PLT W04", "PLT W05", "PLT W06", "PLT W07", "PLT W08", "PLT W09"]
    # 共病
    domain[5] = ["HTN", "DM", "CVA/dementia", "CHF", "Af", "COPD", "Asthma", "Summary Gastrointestinal_bleeding", "Summary Cirrhosis", "Summary ERSD",
               "NewHD", "Summary Active_Cancer", "Summary Cancer_history", "Summary Autoimmunity", "Summary Organ_transplantation"]
    
    print(len(domain[1]), len(val[1]))
    print(len(domain[2]), len(val[2]))
    print(len(domain[3]), len(val[3]))
    print(len(domain[4]), len(val[4]))
    print(len(domain[5]), len(val[5]))

    plt_title = []
    plt_value = []
    for i in range(5,30):
      if i%5==0:
        plt_title.append('domain'+str(i//5))
        plt_value.append(sum(val[i//5]))
      plt_title.append(domain[i//5][val[i//5].index(max(val[i//5]))])
      domain[i//5].remove(domain[i//5][val[i//5].index(max(val[i//5]))])
      plt_value.append(max(val[i//5]))
      val[i//5].remove(max(val[i//5]))
    print(plt_title)
    print(plt_value)
    for i in range(5):
      plt_value[i*6+1] *= (plt_value[i*6] / sum(plt_value[i*6+1:(i+1)*6]))
      plt_value[i*6+2] *= (plt_value[i*6] / sum(plt_value[i*6+1:(i+1)*6]))
      plt_value[i*6+3] *= (plt_value[i*6] / sum(plt_value[i*6+1:(i+1)*6]))
      plt_value[i*6+4] *= (plt_value[i*6] / sum(plt_value[i*6+1:(i+1)*6]))
      plt_value[i*6+5] *= (plt_value[i*6] / sum(plt_value[i*6+1:(i+1)*6]))
    #print(plt_title)
    plt_title.reverse()
    plt_value.reverse()

    plt.figure(figsize=(20,15))
    plt.barh(plt_title, plt_value,color=['cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','navy','cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','navy','cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','navy','cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','cornflowerblue','navy'])
    plt.title('domain Feature Importance')
    plt.xlabel('Importance')
    plt.ylabel('Feature')
    for i, v in enumerate(plt_value):
      color = ''
      if i % 6 == 5: color = 'navy'
      else: color = 'cornflowerblue'
      plt.text(v, i, '%.4f'%(v), color=color, fontweight='bold')
    plt.show()
    plt.savefig('Domain Feature Importance.png')
    
    sp.dependence_plot('RCC APACHEII Total Score',shap_values,x_test,interaction_index=None, dot_size=30, show=False, color='Black')
    plt.savefig('RCC - PDP.png')
    """
    for i in ['PIP', 'ALB', 'PLT', 'HGB']:
      #os.mkdir(i)
      for j in range(1, 10):
        sp.dependence_plot(i+' W0'+str(j),shap_values,x_test,interaction_index=None, dot_size=30, show=False, color='Black')
        plt.savefig(i+'//W'+str(j)+'.png')
    """
    #sp.dependence_plot('EarlyECMO',shap_values,x_test,interaction_index='ECMO')
    #sp.dependence_plot('PSI',shap_values,x_test,interaction_index=None)
    #sp.dependence_plot('RCC_APACHEII',shap_values,x_test,interaction_index=None)
    #sp.dependence_plot('CumuD_4_balance',shap_values,x_test,interaction_index=None)
    
def ExperimentV(x,y,xgbm,rfm,lrm):
    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2,random_state=0)
    numIndex = list(x_test.index)
    print(numIndex)
    temp = x_test
    x_train=x_train.values
    x_test=x_test.values
    y_train=y_train.values
    y_test=y_test.values
    xgbm=xgbm.fit(x_train,y_train)
    explainer=lm.lime_tabular.LimeTabularExplainer(x_test,feature_names=x.columns,class_names=['0', '1'], mode='classification') #'Weaning' 'Mortality'

    for i in range(30):
      print('index(not patient): ', numIndex[i]+2)
      exp=explainer.explain_instance(x_test[i],xgbm.predict_proba,num_features=5)
      #print(x_test[i], xgbm.predict_proba)
      exp.show_in_notebook(show_all=False)
      exp.as_pyplot_figure()
      test = exp.as_pyplot_figure()
      test.tight_layout()
      test.savefig(str(numIndex[i]+2)+".png", figsize=(500, 500), dpi=100)

# --------------------------------------------------
# source: https://medium.com/@peilee_98185/t-%E6%AA%A2%E5%AE%9A-with-python-443c2364b071
def t_test(group1, group2):
    mean1 = np.mean(group1)
    mean2 = np.mean(group2)
    std1 = np.std(group1)
    std2 = np.std(group2)
    nobs1 = len(group1)
    nobs2 = len(group2)
    
    modified_std1 = np.sqrt(np.float32(nobs1)/
                    np.float32(nobs1-1)) * std1
    modified_std2 = np.sqrt(np.float32(nobs2)/
                    np.float32(nobs2-1)) * std2
    statistic, pvalue = scipy.stats.ttest_ind_from_stats(
               mean1=mean1, std1=modified_std1, nobs1=nobs1,
               mean2=mean2, std2=modified_std2, nobs2=nobs2 )
    return statistic, pvalue

# source: https://sites.google.com/site/lisaywtang/tech/python/scikit/auc-conf-interval
def get_ci_auc( y_true, y_pred ): 
    np.random.seed(1234)
    rng=np.random.RandomState(1234)
    from scipy.stats import sem
    from sklearn.metrics import roc_auc_score 
   
    n_bootstraps = 1000   
    bootstrapped_scores = []   
   
    for i in range(n_bootstraps):
        # bootstrap by sampling with replacement on the prediction indices
        indices = rng.random_integers(0, len(y_pred) - 1, len(y_pred))
       
        if len(np.unique(y_true[indices])) < 2:
            # We need at least one positive and one negative sample for ROC AUC
            # to be defined: reject the sample
            continue

        score = roc_auc_score(y_true[indices], y_pred[indices])
        bootstrapped_scores.append(score)   
 
    sorted_scores = np.array(bootstrapped_scores)
    sorted_scores.sort()

   # 90% c.i.
   # confidence_lower = sorted_scores[int(0.05 * len(sorted_scores))]
   # confidence_upper = sorted_scores[int(0.95 * len(sorted_scores))]
 
   # 95% c.i.
    confidence_lower = sorted_scores[int(0.025 * len(sorted_scores))]
    confidence_upper = sorted_scores[int(0.975 * len(sorted_scores))]
   
    return confidence_lower,confidence_upper

# source: https://biasedml.com/tag/model-selection/
def auc(X, Y):
    return 1/(len(X)*len(Y)) * sum([kernel(x, y) for x in X for y in Y])
def kernel(X, Y):
    return .5 if Y==X else int(Y < X)
def structural_components(X, Y):
    V10 = [1/len(Y) * sum([kernel(x, y) for y in Y]) for x in X]
    V01 = [1/len(X) * sum([kernel(x, y) for x in X]) for y in Y]
    return V10, V01
    
def get_S_entry(V_A, V_B, auc_A, auc_B):
    return 1/(len(V_A)-1) * sum([(a-auc_A)*(b-auc_B) for a,b in zip(V_A, V_B)])
def z_score(var_A, var_B, covar_AB, auc_A, auc_B):
    return (auc_A - auc_B)/((var_A + var_B - 2*covar_AB)**(.5))

def group_preds_by_label(preds, actual):
    X = [p for (p, a) in zip(preds, actual) if a]
    Y = [p for (p, a) in zip(preds, actual) if not a]
    return X, Y
def delong(actual, preds_A, preds_B):
    import scipy.stats as st
    X_A, Y_A = group_preds_by_label(preds_A, actual)
    X_B, Y_B = group_preds_by_label(preds_B, actual)
    V_A10, V_A01 = structural_components(X_A, Y_A)
    V_B10, V_B01 = structural_components(X_B, Y_B)
    auc_A = auc(X_A, Y_A)
    auc_B = auc(X_B, Y_B)
    # Compute entries of covariance matrix S (covar_AB = covar_BA)
    var_A = (get_S_entry(V_A10, V_A10, auc_A, auc_A) * 1/len(V_A10)
            + get_S_entry(V_A01, V_A01, auc_A, auc_A) * 1/len(V_A01))
    var_B = (get_S_entry(V_B10, V_B10, auc_B, auc_B) * 1/len(V_B10)
            + get_S_entry(V_B01, V_B01, auc_B, auc_B) * 1/len(V_B01))
    covar_AB = (get_S_entry(V_A10, V_B10, auc_A, auc_B) * 1/len(V_A10)
                + get_S_entry(V_A01, V_B01, auc_A, auc_B) * 1/len(V_A01))
    # Two tailed test
    z = z_score(var_A, var_B, covar_AB, auc_A, auc_B)
    p = st.norm.sf(abs(z))*2
    print(z, p)
# --------------------------------------------------