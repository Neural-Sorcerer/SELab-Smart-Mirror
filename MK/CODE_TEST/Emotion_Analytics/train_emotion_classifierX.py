"""
File: train_emotion_classifierO.py
Date: 2019. 07. 11
Author: MK
Description: Train emotion classification model using logistic regression, Decision tree, SVM, KNN and Naive Bayes
Genearate the trained model for prediction.
"""
import os
from time import time
from operator import itemgetter

import dlib
import cv2
import imutils
from imutils import face_utils

from sklearn import preprocessing, model_selection
import pandas as pd
import numpy as np
from sklearn.externals import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import confusion_matrix, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report
from emotion_factor_dataframe import EmotionFactorAnalyzer

from sklearn.ensemble import BaggingClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.ensemble import VotingClassifier
from sklearn.ensemble import AdaBoostClassifier
import xgboost as xgb


class FactorTraining:
    def __init__(self):
        self.feature_cols = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11']
        self.emotion_distance = pd.read_csv("./datasets/emotion_distance_rate_ckplus.csv")  # load dataset
        self.emotion_distance = self.emotion_distance.sample(frac=1)  # shuffle the data
        self.X = self.emotion_distance[self.feature_cols]  # Features
        self.y = self.emotion_distance.emotion  # Target variable
        # print(self.X)
        # print(self.y)
        # print(self.emotion_distance.head())
        # emotion_distance.info()
        # emotion_distance.describe()

    def prepare_dt(self):
        # split X and y into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(self.X, self.y, test_size=0.25, random_state=0)
        # print("Testx", X_train)
        # print("Testy", y_train)
        # print("Testx", X_test)
        # print("Testy", y_test)

        return X_train, X_test, y_train, y_test

    def generate_models(self):
        print('********************* LOGREG *******************************\n')
        self.train_logreg_model()

        print('\n********************* Decision Tree *******************************')
        self.train_dtree_model()

        print('\n********************* SVM *******************************')
        self.train_svc_model()

        # print('\n********************* SVM hypertune_parameters *******************************')
        # ft.hypertune_parameters(model='svm')

        print('\n********************* KNN *******************************')
        self.train_knn_model()

        # print('\n********************* KNN hypertune_parameters *******************************')
        # ft.hypertune_parameters(model='knn')

        print('\n********************* Naive Bayes *******************************')
        self.train_gnb_model()

    # Bagged Decision Trees
    def train_bagged_ensemble_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()

        # kfold = model_selection.KFold(n_splits=10, random_state=7)
        # model = BaggingClassifier(base_estimator=DecisionTreeClassifier(), n_estimators=100, random_state=7)
        # results = model_selection.cross_val_score(model, self.X, self.y, cv=kfold, scoring='accuracy')  # cv kfold
        # print('>>>>>>Result 1', results.mean())

        bag_clf = BaggingClassifier(DecisionTreeClassifier(), n_estimators=100, random_state=42)
        bag_clf.fit(X_train, y_train)
        # Save the model as a pickle in a file
        joblib.dump(bag_clf, './models/emotion_factor/bag_clf_fer2013_model.pkl')

        # y_pred = bag_clf.predict(X_test)

        accuracy = bag_clf.score(X_test, y_test)
        print('>>>>>>Bagging Classifier Accuracy: ', accuracy)

    # AdaBoost Classification
    def train_adaboost_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()

        # kfold = model_selection.KFold(n_splits=10, random_state=7)
        # model = AdaBoostClassifier(n_estimators=70, random_state=42)
        # results = model_selection.cross_val_score(model, self.X, self.y, cv=kfold)  # cv kfold
        # print('>>>>>>Result 1', results.mean())

        ada_boost_clf = AdaBoostClassifier(n_estimators=100, random_state=42)
        ada_boost_clf.fit(X_train, y_train)

        # Save the model as a pickle in a file
        joblib.dump(ada_boost_clf, './models/emotion_factor/ada_boost_clf_fer2013_model.pkl')

        accuracy = ada_boost_clf.score(X_test, y_test)
        print('>>>>>>AdaBoost Classifier Accuracy: ', accuracy)

    def train_boost_ensemble_mode(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()

        ada_boost = AdaBoostClassifier()
        grad_boost = GradientBoostingClassifier()
        xgb_boost = xgb.XGBClassifier()

        boost_array = [ada_boost, grad_boost, xgb_boost]

        eclf = VotingClassifier(estimators=[('ada_boost', ada_boost),
                                           ('grad_boost', grad_boost),
                                           ('xgb_boost', xgb_boost)], voting='hard')
        # clf.fit(X_train, y_train)

        # labels = ['Ada Boost', 'Grad Boost', 'XG Boost', 'Ensemble']
        # for clf, label in zip([ada_boost, grad_boost, xgb_boost, eclf], labels):
        #     scores = cross_val_score(clf, self.X, self.y, cv=10, scoring='accuracy')
        #     print("Mean: {0:.3f}, std: (+/-) {1:.3f} [{2}]".format(scores.mean(), scores.std(), label))

        for clf in (ada_boost, grad_boost, xgb_boost, eclf):
                clf.fit(X_train, y_train)
                y_pred = clf.predict(X_test)
                print(clf.__class__.__name__, accuracy_score(y_test, y_pred))

    def train_voting_gscv(self):
        tuned_parameters = [{'kernel': ['rbf'], 'gamma': [1e-3, 1e-4],
                             'C': [1, 10, 100, 1000]},
                            {'kernel': ['linear'], 'C': [1, 10, 100, 1000]}]
        clf1 = LogisticRegression(solver='lbfgs', multi_class='multinomial', random_state=42)
        clf2 = SVC(random_state=42, probability=True)
        clf3 = GaussianNB()
        eclf = VotingClassifier(estimators=[('lr', clf1), ('svm', clf2), ('gnb', clf3)], voting='soft')

        params = {'lr__C': [1.0, 100.0], 'svm__kernel': ['linear', 'rbf'], 'svm__C': [1, 10, 100, 1000],
                  'svm__gamma': [1e-3, 1e-4]}

        grid = GridSearchCV(estimator=eclf, param_grid=params, cv=5)
        grid.fit(self.X, self.y)

        # check top performing n_neighbors value
        print('Voting best parameters=', grid.best_params_)
        # check mean score for the top performing value of n_neighbors
        print('Voting accuracy with optimal parameters=', grid.best_score_)

    # Voting Ensemble for Classification
    def train_voting_ensemble_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()
        # kfold = model_selection.KFold(n_splits=10, random_state=7)

        print("---------------------------HARD------------------------------------\n")
        # create the sub models
        estimators = []
        log_clf = LogisticRegression(C=1000, penalty='l1', random_state=42)
        estimators.append(('logistic', log_clf))
        # dtree_clf = DecisionTreeClassifier()
        # estimators.append(('cart', dtree_clf))
        # rnd_clf = RandomForestClassifier(random_state=1)
        # estimators.append(('rnd', rnd_clf))
        svm_clf = SVC(gamma='scale', kernel='linear', C=1000, random_state=42)
        estimators.append(('svm', svm_clf))
        knn_clf = KNeighborsClassifier(n_neighbors=11)
        estimators.append(('knn', knn_clf))
        gnb_clf = GaussianNB()
        estimators.append(('gnb', gnb_clf))

        # # create the ensemble model
        # voting_clf = VotingClassifier(estimators)
        # results = model_selection.cross_val_score(voting_clf, self.X, self.y, cv=5, scoring='accuracy')
        # print('>>>>>>>>>>>>>>Voting 1\n', results.mean())

        # training the hard voting model
        voting_clf_hard = VotingClassifier(estimators, voting='hard')
        voting_clf_hard.fit(X_train, y_train)

        # Save the model as a pickle in a file
        joblib.dump(voting_clf_hard, './models/emotion_factor/voting_clf_hard_ckplus_hyper_hard_model.pkl')
        # Load the model from the file
        # voting_clf_hard = joblib.load('./models/emotion_factor/voting_clf_hard_model.pkl')

        # y_pred = voting_clf_hard.predict(X_test)

        # accuracy of each classifier (dtree_clf, )
        for clf in (log_clf, svm_clf, knn_clf, gnb_clf, voting_clf_hard):
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)
            print(clf.__class__.__name__, accuracy_score(y_test, y_pred))

        # print("*********************************\n")
        # # accuracy of each classifier 2
        # for clf, label in zip([log_clf, dtree_clf, svm_clf, knn_clf, gnb_clf, voting_clf],
        #                       ['Logistic Regression', 'Decision Tree', 'SVM', 'KNN', 'naive Bayes', 'Ensemble']):
        #     scores = cross_val_score(clf, self.X, self.y, cv=5, scoring='accuracy')
        #     print(">>>>>>>>>>>>>>Hard Voting 2: All dataset\nAccuracy: %0.2f (+/- %0.2f) [%s]" % (scores.mean(),
        #                                                                                           scores.std(), label))
        #
        print("---------------------------SOFT------------------------------------\n")
        # create the sub models
        estimators2 = []
        log_clf = LogisticRegression(C=1000, penalty='l1', random_state=42)
        estimators2.append(('logistic', log_clf))
        # dtree_clf = DecisionTreeClassifier()
        # estimators2.append(('cart', dtree_clf))
        # rnd_clf = RandomForestClassifier(random_state=1)
        # estimators.append(('rnd', rnd_clf))
        svm_clf = SVC(gamma='scale', kernel='linear', C=1000, random_state=42, probability=True)
        estimators2.append(('svm', svm_clf))
        knn_clf = KNeighborsClassifier(n_neighbors=11)
        estimators2.append(('knn', knn_clf))
        gnb_clf = GaussianNB()
        estimators2.append(('gnb', gnb_clf))

        # training the soft voting model
        voting_clf_soft = VotingClassifier(estimators2, voting='soft')
        voting_clf_soft.fit(X_train, y_train)

        # Save the model as a pickle in a file
        joblib.dump(voting_clf_soft, './models/emotion_factor/voting_clf_soft_ckplus_hyper_soft_model.pkl')
        # Load the model from the file
        # voting_clf_soft = joblib.load('./models/emotion_factor/voting_clf_soft_model.pkl')

        # y_pred = voting_clf_soft.predict(X_test)

        # accuracy of each classifier (dtree_clf,)
        for clf in (log_clf, svm_clf, knn_clf, gnb_clf, voting_clf_soft):
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)
            print(clf.__class__.__name__, accuracy_score(y_test, y_pred))

        # print("*********************************\n")
        # # accuracy of each classifier 2
        # for clf, label in zip([log_clf, dtree_clf, svm_clf, knn_clf, gnb_clf, voting_clf_soft],
        #                       ['Logistic Regression', 'Decision Tree', 'SVM', 'KNN', 'naive Bayes', 'Ensemble']):
        #     scores = cross_val_score(clf, self.X, self.y, cv=5, scoring='accuracy')
        #     print(">>>>>>>>>>>>>>Soft voting 2: All dataset\nAccuracy: %0.2f (+/- %0.2f) [%s]" % (scores.mean(),
        #                                                                                           scores.std(), label))

    def train_logreg_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()
        logmodel = LogisticRegression(C=1, random_state=42)  # instantiate the model (using the default parameters)
        logmodel.fit(X_train, y_train)

        joblib.dump(logmodel, './models/emotion_factor/logmodel_model.pkl')  # Save the model as a pickle in a file
        logmodel_from_joblib = joblib.load('./models/emotion_factor/logmodel_model.pkl')  # Load the model from the file
        logmodel_predictions = logmodel_from_joblib.predict(X_test)  # Use the loaded model to make predictions
        # print(logmodel_predictions)

        # creating a confusion matrix
        cm = confusion_matrix(y_test, logmodel_predictions)
        print('Confusion matrix\n', cm)

        # model accuracy for X_test
        accuracy = logmodel_from_joblib.score(X_test, y_test)
        print('Accuracy of saved model  = ', accuracy)
        # Check that the loaded model is the same as the original
        assert logmodel.score(X_test, y_test) == logmodel_from_joblib.score(X_test, y_test)

        return

    def train_dtree_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()
        # training a DescisionTreeClassifier
        dtree_model = DecisionTreeClassifier(max_depth=2, random_state=42).fit(X_train, y_train)

        joblib.dump(dtree_model, './models/emotion_factor/dtree_model.pkl')  # Save the model as a pickle in a file
        dtree_from_joblib = joblib.load('./models/emotion_factor/dtree_model.pkl')  # Load the model from the file
        dtree_predictions = dtree_from_joblib.predict(X_test)  # Use the loaded model to make predictions
        # print(dtree_predictions)

        # creating a confusion matrix
        cm = confusion_matrix(y_test, dtree_predictions)
        print('Confusion matrix\n', cm)

        # model accuracy for X_test
        accuracy = dtree_from_joblib.score(X_test, y_test)
        print('Accuracy of saved model = ', accuracy)
        # Check that the loaded model is the same as the original
        assert dtree_model.score(X_test, y_test) == dtree_from_joblib.score(X_test, y_test)

        # cross-validation
        depth = []
        for i in range(2, 20):
            clf = DecisionTreeClassifier(max_depth=i, random_state=42)
            # Perform 5-fold cross validation
            cv_scores = cross_val_score(estimator=clf, X=self.X, y=self.y, cv=5, n_jobs=4)
            depth.append((i, cv_scores.mean()))
        print('Decision Tree Cross validation\n', cv_scores)
        print("SVM CV mean accuracy: %0.2f (+/- %0.2f)" % (cv_scores.mean(), cv_scores.std() * 2))
        print('Decision Tree Cross validation\n', depth)

        return

    def train_svc_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()
        # print('test value\n', X_test)
        t0 = time()
        svm_model_linear = SVC(gamma='scale', kernel='linear',
                               C=1000, random_state=42, probability=True).fit(X_train, y_train)  # random parameter
        print('training time: ', round(time() - t0, 3), 's')

        joblib.dump(svm_model_linear, './models/emotion_factor/svmproba_model.pkl')  # Save the model as a pickle in a file
        svm_from_joblib = joblib.load('./models/emotion_factor/svmproba_model.pkl')  # Load the model from the file
        svm_predictions = svm_from_joblib.predict(X_test)  # Use the loaded model to make predictions
        # print(svm_predictions)

        # creating a confusion matrix
        cm = confusion_matrix(y_test, svm_predictions)
        print('Confusion matrix\n', cm)

        # model accuracy for X_test
        accuracy = svm_from_joblib.score(X_test, y_test)
        print('Accuracy of saved model = ', accuracy)
        # Check that the loaded model is the same as the original
        assert svm_model_linear.score(X_test, y_test) == svm_from_joblib.score(X_test, y_test)

        # cross-validation
        clf = SVC(gamma='scale', kernel='linear', C=1000, random_state=42, probability=True)
        cv_scores = cross_val_score(clf, self.X, self.y, cv=5)  # cv= number of time the score is computed

        # print each cv score (accuracy) and average them
        print('SVM Cross validation\n', cv_scores)
        print("SVM CV mean accuracy: %0.2f (+/- %0.2f)" % (cv_scores.mean(), cv_scores.std() * 2))

        return

    def train_knn_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()
        knn = KNeighborsClassifier(n_neighbors=10).fit(X_train, y_train)  # random parameter

        joblib.dump(knn, './models/emotion_factor/knn_model.pkl')  # Save the model as a pickle in a file
        knn_from_joblib = joblib.load('./models/emotion_factor/knn_model.pkl')  # Load the model from the file
        knn_predictions = knn_from_joblib.predict(X_test)  # Use the loaded model to make predictions
        # print(knn_predictions)

        # creating a confusion matrix
        cm = confusion_matrix(y_test, knn_predictions)
        print('Confusion matrix\n', cm)

        # model accuracy for X_test
        accuracy = knn_from_joblib.score(X_test, y_test)
        print('Accuracy = ', accuracy)
        # Check that the loaded model is the same as the original
        assert knn.score(X_test, y_test) == knn_from_joblib.score(X_test, y_test)

        # cross-validation
        knn_cv = KNeighborsClassifier(n_neighbors=30)
        cv_scores = cross_val_score(knn_cv, self.X, self.y, cv=5)  # cv= number of time the score is computed

        # print each cv score (accuracy) and average them
        print('Knn cross validation\n', cv_scores)
        print("KNN CV mean accuracy: %0.2f (+/- %0.2f)" % (cv_scores.mean(), cv_scores.std() * 2))  # mean accuracy
        # print('cv_scores mean: {}'.format(np.mean(cv_scores)))

        return

    def train_gnb_model(self):
        X_train, X_test, y_train, y_test = self.prepare_dt()
        # print(X_test)
        gnb = GaussianNB().fit(X_train, y_train)

        joblib.dump(gnb, './models/emotion_factor/gnb_model.pkl')  # Save the model as a pickle in a file
        gnb_from_joblib = joblib.load('./models/emotion_factor/gnb_model.pkl')  # Load the model from the file
        gnb_predictions = gnb_from_joblib.predict(X_test)  # Use the loaded model to make predictions
        # print(gnb_predictions)

        # creating a confusion matrix
        cm = confusion_matrix(y_test, gnb_predictions)
        print('Confusion matrix\n', cm)

        # model accuracy for X_test
        accuracy = gnb.score(X_test, y_test)
        print('Accuracy = ', accuracy)
        # Check that the loaded model is the same as the original
        assert gnb.score(X_test, y_test) == gnb_from_joblib.score(X_test, y_test)

        return

    def hypertune_parameters(self, model=''):
        if model == 'log':
            X_train, X_test, y_train, y_test = self.prepare_dt()

            # create new a knn model
            logreg = LogisticRegression(random_state=42)

            # create a dictionary of all values we want to test for n_neighbors
            param_grid = {'C': np.logspace(0, 4, 10), "penalty": ["l1", "l2"]}

            # use gridsearch to test all values for n_neighbors
            logreg_gscv = GridSearchCV(logreg, param_grid, cv=5, scoring='accuracy')

            # fit model to data
            logreg_gscv.fit(X_train, y_train)

            # check top performing n_neighbors value
            print('logreg best parameters=', logreg_gscv.best_params_)
            # check mean score for the top performing value of n_neighbors
            print('logreg accuracy with optimal parameters=', logreg_gscv.best_score_)
            print('logreg best estimator=', logreg_gscv.best_estimator_)

        if model == 'knn':
            X_train, X_test, y_train, y_test = self.prepare_dt()

            # create new a knn model
            knn2 = KNeighborsClassifier()

            # create a dictionary of all values we want to test for n_neighbors
            param_grid = {'n_neighbors': np.arange(1, 31)}

            # use gridsearch to test all values for n_neighbors
            knn_gscv = GridSearchCV(knn2, param_grid, cv=5, scoring = 'accuracy')

            # fit model to data
            knn_gscv.fit(X_train, y_train)

            # check top performing n_neighbors value
            print('Knn best parameters=', knn_gscv.best_params_)
            # check mean score for the top performing value of n_neighbors
            print('Knn accuracy with optimal parameters=', knn_gscv.best_score_)
            print('Knn best estimator=', knn_gscv.best_estimator_)

        elif model == 'svm':
            X_train, X_test, y_train, y_test = self.prepare_dt()

            svm = SVC(gamma="scale")
            # create a dictionaries of all values we want to test by cross-validation
            tuned_parameters = [{'kernel': ['rbf'], 'gamma': [1e-3, 1e-4],
                                 'C': [1, 10, 100, 1000]},
                                {'kernel': ['linear'], 'C': [1, 10, 100, 1000]}]
            scores = ['precision', 'recall']

            for score in scores:
                print("# Tuning hyper-parameters for %s" % score)
                print()

                # create new a svm model
                clf = GridSearchCV(svm, tuned_parameters, cv=5, scoring='%s_macro' % score)
                clf.fit(X_train, y_train)

                print("Best parameters set found on development set:\n")
                print(clf.best_params_)
                print("\nGrid scores on development set:\n")
                means = clf.cv_results_['mean_test_score']
                stds = clf.cv_results_['std_test_score']
                for mean, std, params in zip(means, stds, clf.cv_results_['params']):
                    print("%0.3f (+/-%0.03f) for %r" % (mean, std * 2, params))

                print("\nDetailed classification report:\n")
                print("The model is trained on the full development set.\n")
                print("The scores are computed on the full evaluation set.")
                y_true, y_pred = y_test, clf.predict(X_test)
                print(classification_report(y_true, y_pred))


class FactorDetector:
    def __init__(self):
        # Load the model from the files
        self.svm_model = joblib.load('.\\models\\emotion_factor\\svm_model.pkl')
        self.svmproba_model = joblib.load('.\\models\\emotion_factor\\svmproba_model.pkl')
        self.log_model_path = joblib.load('.\\models\\emotion_factor\\logmodel_model.pkl')
        self.gnb_model_path = joblib.load('.\\models\\emotion_factor\\gnb_model.pkl')
        self.vhard_model_path = joblib.load('.\\models\\emotion_factor\\voting_clf_hard_ckplus_hyper_hard_model.pkl')
        self.vsoft_model_path = joblib.load('.\\models\\emotion_factor\\voting_clf_soft_ckplus_hyper_soft_model.pkl')

        self.efa = EmotionFactorAnalyzer()  # emotion factor analyzer object
        self.detector = dlib.get_frontal_face_detector()
        self.predictor_path = "./models/shape_predictor_81_face_landmarks.dat"
        self.predictor = dlib.shape_predictor(self.predictor_path)

    def detect_emotion_distance_factor(self, frame):
        result_display, error, emotion_label = {}, '', ''

        # load the input image
        # frame = cv2.imread(frame)
        shape = frame.shape
        # print('Original shape: ', shape[:])
        # cv2.imshow("Original image", frame)
        # cv2.waitKey(1)

        while shape:
            if shape[0] < 300 or shape[1] < 300:  # check image size and preprocess
                error = 'Image size incorrect, but was resized.'
                print(error)
                # frame = imutils.resize(frame, width=500)
                shape = frame.shape
                # print('Resized shape: ', shape[:])
                # cv2.imshow("Resized image", frame)
                # cv2.waitKey(1)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = self.detector(gray, 1)  # detect faces in the grayscale image
            if len(rects) != 1:  # check only one person
                error = 'Face no detected'
                print(error)
                break

            target_face = rects[0]
            height = target_face.height()
            width = target_face.width()
            if height < 150 or width < 150:  # check face part size to detect
                error = 'Detected face size incorrect'
                print(error)
                break

            # # Crop face part include hear and neck
            # img_cropped = frame[target_face.top() - 50:target_face.bottom() + 80,
            #               target_face.left() - 50:target_face.right() + 50]
            # # cv2.imshow("Cropped image", img_cropped)
            # # cv2.waitKey(1)
            #
            # img_resize = imutils.resize(img_cropped, width=500)
            # # cv2.imshow("Resized image", img_resize)
            # # cv2.waitKey(1)
            result_display, emotion_label = self.detect_emotion_computation(rects, gray, frame)
            break

        return error, result_display, emotion_label

    def detect_emotion_computation(self, rects, gray, img_resize):
        # global face_shape
        result = {}
        error = ''
        emotion_label = ''
        emotions = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']
        models = {'SVC': self.svm_model, 'SVCPROBA': self.svmproba_model, 'Logistic Regression': self.log_model_path,
                  'Naive Bayes': self.gnb_model_path, 'Hard': self.vhard_model_path, 'Soft': self.vsoft_model_path}

        # loop over the face detected
        for (i, rect) in enumerate(rects[0:1]):
            # determine the facial landmarks for the face region, then convert the facial landmark
            # (x, y)-coordinates to a NumPy array
            face_shape = self.predictor(gray, rect)
            # print('face shape:', face_shape)
            mtx_landmarks = np.matrix([[p.x, p.y] for p in face_shape.parts()])
            face_shape = np.squeeze(np.asarray(mtx_landmarks))
            # print('Numpy face shape:', face_shape)

            # convert dlib's rectangle to a OpenCV-style bounding box
            # [i.e., (x, y, w, h)], then draw the face bounding box
            (x, y, w, h) = face_utils.rect_to_bb(rect)
            cv2.rectangle(img_resize, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # show the face number
            cv2.putText(img_resize, "Face #{}".format(i + 1), (x - 10, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # loop over the (x, y)-coordinates for the facial landmarks and draw them on the image
            k = 0
            for (x, y) in face_shape[:]:
                cv2.circle(img_resize, (x, y), 1, (0, 0, 255), -1)
                cv2.putText(img_resize, str(k), (x, y), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.3, (0, 255, 0))
                k += 1

            # cv2.imwrite(save_path, gray)  # Save cropped gray image

        # Compute the distance of the factors
        result, distance_vector = self.efa.compute_factors(face_shape, emotion_label)
        # print('Distance result ', result, type(result))

        # round the value computed
        for k, v in result.items():
            result[k] = round(v, 2)

        # print('f1:The distance between the right eye and the right eyebrow:', result['f1'])
        # print('f2:The distance between the left eye and the left eyebrow:', result['f2'])
        # print('f3:The distance between the inner ends of the eyebrows:', result['f3'])
        # print('f4:The distance between the outer corner of the right eye and the corner of the mouth:',
        #       result['f4'])
        # print('f5:The distance between the outer corner of the left eye and the corner of the mouth:', result['f5'])
        # print('f6:The distance of the right eyelid from the right eyebrow:', result['f6'])
        # print('f7:The distance of the left eyelid from the left eyebrow:', result['f7'])
        # print('f8: The distance of the right upper and lower eyelids:', result['f8'])
        # print('f9: The distance of the left upper and lower eyelids:', result['f9'])
        # print('f10: The distance between the upper and lower lip:', result['f10'])
        # print('f11: The distance between the outer ends of the mouth:', result['f11'])

        # prepare distance dictionary for displaying
        result_display = {key: result[key] for key in ['f8', 'f9', 'f10', 'f11']}
        # print(result_display)

        # delete the emotion colon from the dictionary
        del distance_vector['emotion']
        # print('Distance vector 2', distance_vector, type(distance_vector))

        # create the dataframe from the dictionary
        df = pd.DataFrame(distance_vector)
        # print('Data frame\n', df)
        # print('Data frame values\n', df.values)

        emotion_proba = models['Soft'].predict_proba(df.values)[0]  # Use the loaded model to make predictions
        emotion_higest_proba = max(emotion_proba)
        # print(emotion_higest_proba)

        emotion_prediction = models['Soft'].predict(df.values)  # Use the loaded model to make predictions
        value_predicted = int("".join(map(str, emotion_prediction)))
        # Get the corresponding emotion label from the table made
        emotion_label = emotions[value_predicted]
        # print('\nEmotion predicted\nValue: {} \nEmotion: {}'.format(value_predicted, emotion_label))
        print('\nEmotion predicted\nValue:{}\nEmotion: {}'.format(value_predicted, emotion_label))

        # compare the emotions probability and return the higest
        proba_comparison = {emotion_label: emotion_higest_proba, 'Sad': 0.5338546390074583}
        emotion_label = self.compare_emotion(proba_comparison)

        # show the output image with the face detections + facial landmarks
        # cv2.imshow("Resized image+Landmarks", img_resize)
        # cv2.waitKey(0)

        return result, emotion_label

    def compare_emotion(self, proba_comparison):
        print('\nLabel proba comparison\n', proba_comparison)
        label = max(proba_comparison, key=proba_comparison.get)
        print(' Final label is : ', label)

        return label


if __name__ == '__main__':
    ft = FactorTraining()
    # print('********************* LOGREG *******************************\n')
    # ft.train_logreg_model()
    # print('\n********************* Decision Tree *******************************')
    # ft.train_dtree_model()
    # print('\n********************* SVM *******************************')
    # ft.train_svc_model()
    # print('\n********************* LogReg hypertune_parameters *******************************')
    # ft.hypertune_parameters(model='log')
    # print('\n********************* SVM hypertune_parameters *******************************')
    # ft.hypertune_parameters(model='svm')
    # print('\n********************* KNN *******************************')
    # ft.train_knn_model()
    # print('\n********************* KNN hypertune_parameters *******************************')
    # ft.hypertune_parameters(model='knn')
    # print('\n********************* Naive Bayes *******************************')
    # ft.train_gnb_model()
    # print('\n********************* Bagging based Ensembling *******************************')
    # ft.train_bagged_ensemble_model()
    # print('\n********************* AdaBoost model *******************************')
    # ft.train_adaboost_model()
    # print('\n********************* Boost Ensemble *******************************')
    # ft.train_boost_ensemble_mode()
    # print('\n********************* Voting Ensembling *******************************')
    # ft.train_voting_ensemble_model()
    # print('\n********************* Voting Ensembling + gridSearch *******************************')
    # ft.train_voting_gscv()


    # img = 'test/sad0.jpg'
    # factor_detector = FactorDetector()
    # error, result, emotion = factor_detector.detect_emotion_distance_factor(img)
    # print('Error: ', error)
    # print('Distance computed out of 11 factors\n{} \nEmotion: {}'.format(result, emotion))

    video = cv2.VideoCapture(0)
    while True:
        a, frame = video.read()
        factor_detector = FactorDetector()
        error, result, emotion = factor_detector.detect_emotion_distance_factor(frame)
        print('Error: ', error)
        print(result)
        cv2.imshow('frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
